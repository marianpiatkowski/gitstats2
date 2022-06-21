# -*- python-indent-offset: 4 -*-
"""
Copyright (C) 2021-  Marian Piatkowski

This file is a part of GitStats2.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import sys
import getopt
import os
import subprocess
import time
import datetime
import re
import calendar
import collections
from enum import IntEnum
from multiprocessing import Pool
from collections import namedtuple
from collections import Counter
from functools import partial

if sys.version_info < (3, 6) :
    print("Python 3.6 or higher is required for gitstats2", file=sys.stderr)
    sys.exit(1)

def cwd_git() :
    success = False
    try :
        subprocess.check_call(
            'git rev-parse --show-toplevel',
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=True)
        success = True
    except subprocess.CalledProcessError :
        success = False
    return success

def get_pipe_output(cmds, quiet=False) :
    start = time.time()
    cmd = ' | '.join(cmds)
    if not quiet and os.isatty(1) :
        print('>> ' + cmd, end=' ')
        sys.stdout.flush()
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True,
        encoding='utf8')
    output = process.communicate()[0]
    end = time.time()
    if not quiet :
        if os.isatty(1) :
            print('\r', end=' ')
        print(f"[{(end-start):.5f}] >> {' | '.join(cmds)}")
    get_pipe_output.exectime_commands += (end - start)
    return output.rstrip('\n')

get_pipe_output.exectime_commands = 0.0

# ****************************************************************************************
# ****************************************************************************************

class GitStatisticsParallel :
    @staticmethod
    def ext_lines_by_blob(ext_blob, processes) :
        with Pool(processes=processes) as pool :
            ext_linecount = pool.starmap(GitStatisticsParallel.add_linecount, ext_blob)
            pool.terminate()
            pool.join()
        return ext_linecount

    @staticmethod
    def add_linecount(ext, blob_id) :
        cmd = f"git cat-file blob {blob_id}"
        pipe_out = get_pipe_output([cmd, 'wc -l'])
        return (ext, int(pipe_out))

    @staticmethod
    def file_tree_by_revlist(lines, processes, quiet=False) :
        with Pool(processes=processes) as pool :
            time_files_commit = pool.map(
                partial(GitStatisticsParallel.add_time_files_commit,
                        quiet=quiet),
                lines)
            pool.terminate()
            pool.join()
        return time_files_commit

    @staticmethod
    def add_time_files_commit(line, quiet) :
        timestamp, rev, commit_hash = line.split()
        pipe_out = get_pipe_output([f"git ls-tree -r \"{rev}\""], quiet=quiet)
        file_tree = GitStatisticsParallel.file_tree_by_revision(pipe_out)
        return (timestamp, file_tree, commit_hash)

    @staticmethod
    def file_tree_by_revision(pipe_out) :
        lines = pipe_out.split('\n')
        lines_splitted = list(map(lambda line : re.split(r'\s+', line, 4), lines))
        # skip submodules
        lines_filtered = list(filter(lambda line : line[0] != '160000', lines_splitted))
        return [el for *_, el in lines_filtered]

    @staticmethod
    def lines_by_authors(file_tree, commit_hash, processes) :
        with Pool(processes=processes) as pool :
            lines_by_authors_list = pool.map(
                partial(GitStatisticsParallel.add_lines_by_authors,
                        commit_hash=commit_hash),
                file_tree)
            pool.terminate()
            pool.join()
        return sum(lines_by_authors_list, collections.Counter())

    @staticmethod
    def add_lines_by_authors(revfile, commit_hash) :
        cmd = f"git blame --line-porcelain {commit_hash} -- {revfile}"
        pipe_out = get_pipe_output([cmd, "sed -n 's/^author //p'"], quiet=True)
        return Counter(pipe_out.split('\n'))

# ****************************************************************************************
# ****************************************************************************************

class LogShortStatParserError(Exception) :
    def __init__(self, message, value) :
        super().__init__()
        self.message = message
        self.value = value

class ShortStatParserState(IntEnum) :
    Initial = 0
    CommitInfo = 1
    ChangesByCommit = 2
    MaxStates = 3

class ShortStatStateInitial :
    @staticmethod
    def decide(parser, line) :
        try :
            stamp = line.split(' ')[0]
            datetime.datetime.fromtimestamp(int(stamp))
            parser.toggle(ShortStatParserState.CommitInfo)
        except ValueError as value_error :
            if re.search('files? changed', line) is not None :
                parser.toggle(ShortStatParserState.ChangesByCommit)
            else :
                raise LogShortStatParserError('Could not parse line: ', line) from value_error

class ShortStatStateCommitInfo :
    @staticmethod
    def decide(parser, line) :
        target_state = ShortStatParserState.CommitInfo
        if not line :
            target_state = ShortStatParserState.Initial
        elif re.search('files? changed', line) is not None :
            target_state = ShortStatParserState.ChangesByCommit
        parser.toggle(target_state)

class ShortStatStateChangesByCommit :
    @staticmethod
    def decide(parser, line) :
        if not line :
            parser.toggle(ShortStatParserState.Initial)
        else :
            try :
                stamp = line.split(' ')[0]
                datetime.datetime.fromtimestamp(int(stamp))
                parser.toggle(ShortStatParserState.CommitInfo)
            except ValueError as value_error :
                raise LogShortStatParserError('Could not parse line: ', line) from value_error

CommitChangesTuple = namedtuple('CommitChangesTuple', 'files inserted deleted')

class GitStatisticsBase :
    def __init__(self, conf, gitpaths) :
        self.configuration = conf.copy()
        self.gitpaths = gitpaths
        self.runstart_stamp = float(0.0)
        self._authors_of_repository = {}

    @staticmethod
    def get_gitstats2_version() :
        gitstats_repo = os.path.dirname(os.path.abspath(__file__))
        commit_range = '@'
        cmd = f"git --git-dir={gitstats_repo}/.git --work-tree={gitstats_repo} \
rev-parse --short {commit_range}"
        return get_pipe_output([cmd])

    @staticmethod
    def get_git_version() :
        return get_pipe_output(['git --version'])

    @staticmethod
    def decompose_gitpath(gitpath) :
        top_level_gitpath = get_pipe_output(
            [f"git -C {gitpath} rev-parse --show-toplevel"], quiet=True)
        subdir_gitpath = get_pipe_output(
            [f"git -C {gitpath} rev-parse --show-prefix"], quiet=True)
        return (top_level_gitpath, subdir_gitpath)

    @staticmethod
    def get_prefixed_path(subdir_path) :
        if not subdir_path :
            return ''
        return f"-- {subdir_path}"

    def get_log_range(self, default_range='HEAD', end_only=True) :
        commit_range = self.get_commit_range(default_range, end_only)
        if self.configuration['start_date'] :
            return f"--since=\"{self.configuration['start_date']}\" \"{commit_range}\""
        return commit_range

    def get_commit_range(self, default_range='HEAD', end_only=True) :
        if self.configuration['commit_end'] :
            if end_only or not self.configuration['commit_begin'] :
                return self.configuration['commit_end']
            return f"{self.configuration['commit_begin']}..{self.configuration['commit_end']}"
        return default_range

    def get_runstart_stamp(self) :
        return self.runstart_stamp

    def collect(self) :
        pass

# ****************************************************************************************
# ****************************************************************************************

class LogShortStatParser :
    def __init__(self) :
        self.decide_in_state = (
            ShortStatStateInitial.decide,
            ShortStatStateCommitInfo.decide,
            ShortStatStateChangesByCommit.decide )
        self.current_state = ShortStatParserState.Initial

    def decide(self, line) :
        self.decide_in_state[self.current_state](self, line)

    def toggle(self, target_state) :
        self.current_state = target_state

class LogShortStatData(GitStatisticsBase, LogShortStatParser) :
    def __init__(self, conf, gitpaths) :
        super().__init__(conf, gitpaths)
        LogShortStatParser.__init__(self)
        self.total_lines = {}
        self.total_lines_added = {}
        self.total_lines_removed = {}

        self.changes_by_date = {}
        self.lines_added_by_month = {}
        self.lines_removed_by_month = {}
        self.lines_added_by_year = {}
        self.lines_removed_by_year = {}
        self.changes_by_date_by_author = {}

        self._process_in_state = [
            [self.do_nothing,] * ShortStatParserState.MaxStates
            for i in range(ShortStatParserState.MaxStates) ]
        self.process_current_state = \
            self._process_in_state[
                ShortStatParserState.Initial][ShortStatParserState.Initial]
        self._process_in_state[
            ShortStatParserState.Initial][
                ShortStatParserState.ChangesByCommit] = self._set_changes_by_commit
        self._process_in_state[
            ShortStatParserState.CommitInfo][
                ShortStatParserState.ChangesByCommit] = self._set_changes_by_commit
        self._changes_by_commit = None

    def get_total_lines_of_code(self) :
        return sum(self.total_lines.values())

    def get_total_lines_added(self) :
        return sum(self.total_lines_added.values())

    def get_total_lines_removed(self) :
        return sum(self.total_lines_removed.values())

    def get_changes_by_date(self) :
        return self.changes_by_date

    def get_changes_by_date_by_author(self) :
        return self.changes_by_date_by_author

    def get_lines_added_by_month(self) :
        return self.lines_added_by_month

    def get_lines_added_by_year(self) :
        return self.lines_added_by_year

    def get_lines_removed_by_month(self) :
        return self.lines_removed_by_month

    def get_lines_removed_by_year(self) :
        return self.lines_removed_by_year

    @staticmethod
    def do_nothing(_repository, _line) :
        pass

    def collect(self) :
        self.runstart_stamp = time.time()
        repo_names = []
        for gitpath in self.gitpaths :
            print(f"Git path: {gitpath}")
            prev_dir = os.getcwd()
            os.chdir(gitpath)
            print('Collecting data...')
            self._authors_of_repository = {}
            repository = os.path.basename(os.path.abspath(gitpath))
            repo_names.append(repository)
            self._collect_lines_modified(repository)
            self._collect_lines_modified_by_author(repository)
            os.chdir(prev_dir)
        if not self.configuration['project_name'] :
            self.configuration['project_name'] = ', '.join(repo_names)

    def _set_changes_by_commit(self, _, line) :
        self._changes_by_commit = self._get_modified_counts(line)

    def _collect_lines_modified(self, repository) :
        self.current_state = ShortStatParserState.Initial
        self._process_in_state[
            ShortStatParserState.ChangesByCommit][
                ShortStatParserState.CommitInfo] = self._update_lines_modified
        extra = ''
        if self.configuration['linear_linestats'] :
            extra = '--first-parent -m'
        cmd = f"git log --shortstat {extra} --pretty=format:\"%at %aN\" \
{self.get_log_range('HEAD')}"
        pipe_out = get_pipe_output([cmd])
        lines = pipe_out.split('\n')
        for line in reversed(lines) :
            # Outputs:
            # N files changed, N insertions (+), N deletions (-)
            # <stamp> <author>
            self.decide(line)
            self.process_current_state(repository, line)
        self._process_in_state[
            ShortStatParserState.ChangesByCommit][
                ShortStatParserState.CommitInfo] = self.do_nothing

    def _collect_lines_modified_by_author(self, repository) :
        self.current_state = ShortStatParserState.Initial
        self._process_in_state[
            ShortStatParserState.ChangesByCommit][
                ShortStatParserState.CommitInfo] = self._update_lines_modified_by_author
        self._process_in_state[
            ShortStatParserState.CommitInfo][
                ShortStatParserState.CommitInfo] = self._update_merge_commit
        cmd = f"git log --shortstat --date-order --pretty=format:\"%at %aN\" \
{self.get_log_range('@')}"
        pipe_out = get_pipe_output([cmd])
        lines = pipe_out.split('\n')
        for line in reversed(lines) :
            self.decide(line)
            self.process_current_state(repository, line)
        self._process_in_state[
            ShortStatParserState.ChangesByCommit][
                ShortStatParserState.CommitInfo] = self.do_nothing
        self._process_in_state[
            ShortStatParserState.CommitInfo][
                ShortStatParserState.CommitInfo] = self.do_nothing

    def toggle(self, target_state) :
        self.process_current_state = self._process_in_state[self.current_state][target_state]
        self.current_state = target_state

    @staticmethod
    def _get_modified_counts(line) :
        numbers = tuple(map(int, re.findall(r'\d+', line)))
        if len(numbers) == 1 :
            changes_by_commit = CommitChangesTuple(numbers[0], inserted=0, deleted=0)
        elif len(numbers) == 2 and line.find('(+)') != -1 :
            changes_by_commit = CommitChangesTuple(numbers[0], inserted=numbers[1], deleted=0)
        elif len(numbers) == 2 and line.find('(-)') != -1 :
            changes_by_commit = CommitChangesTuple(numbers[0], inserted=0, deleted=numbers[1])
        else :
            changes_by_commit = CommitChangesTuple(numbers[0], inserted=numbers[1], deleted=numbers[2])
        return changes_by_commit

    def _update_lines_modified(self, repository, line) :
        stamp = line.split(' ')[0]
        date = datetime.datetime.fromtimestamp(int(stamp))
        # meld stamp and repository into a single key
        stamp_key = ' '.join([stamp, repository])
        (files, inserted, deleted) = self._changes_by_commit
        self._update_total_lines(repository, inserted, deleted)
        self.changes_by_date[stamp_key] = {
            'files' : files,
            'inserted' : inserted,
            'deleted' : deleted,
            'lines' : self.total_lines.get(repository, 0) }
        self._update_lines_modified_by_month(date, inserted, deleted)
        self._update_lines_modified_by_year(date, inserted, deleted)

    def _update_total_lines(self, repository, inserted, deleted) :
        self.total_lines[repository] = self.total_lines.get(repository, 0) + inserted
        self.total_lines[repository] -= deleted
        self.total_lines_added[repository] = self.total_lines_added.get(repository, 0) + inserted
        self.total_lines_removed[repository] = self.total_lines_removed.get(repository, 0) + deleted

    def _update_lines_modified_by_month(self, date, inserted, deleted) :
        yymm = date.strftime('%Y-%m')
        self.lines_added_by_month[yymm] = self.lines_added_by_month.get(yymm, 0) + inserted
        self.lines_removed_by_month[yymm] = self.lines_removed_by_month.get(yymm, 0) + deleted

    def _update_lines_modified_by_year(self, date, inserted, deleted) :
        year = date.year
        self.lines_added_by_year[year] = self.lines_added_by_year.get(year, 0) + inserted
        self.lines_removed_by_year[year] = self.lines_removed_by_year.get(year, 0) + deleted

    def _update_lines_modified_by_author(self, repository, line) :
        splitted_line = line.split(' ')
        stamp = splitted_line[0]
        # meld stamp and repository into a single key
        stamp_key = ' '.join([stamp, repository])
        author = ' '.join(splitted_line[1:])
        (_, inserted, deleted) = self._changes_by_commit
        if author not in self._authors_of_repository :
            self._authors_of_repository[author] = \
                {'lines_added' : 0, 'lines_removed' : 0, 'commits' : 0}
        self._authors_of_repository[author]['commits'] = \
            self._authors_of_repository[author].get('commits', 0) + 1
        self._authors_of_repository[author]['lines_added'] = \
            self._authors_of_repository[author].get('lines_added', 0) + inserted
        self._authors_of_repository[author]['lines_removed'] = \
            self._authors_of_repository[author].get('lines_removed', 0) + deleted
        if stamp_key not in self.changes_by_date_by_author :
            self.changes_by_date_by_author[stamp_key] = {}
        if author not in self.changes_by_date_by_author[stamp_key] :
            self.changes_by_date_by_author[stamp_key][author] = {}
        self.changes_by_date_by_author[stamp_key][author]['lines_added'] = inserted
        self.changes_by_date_by_author[stamp_key][author]['lines_removed'] = deleted
        self.changes_by_date_by_author[stamp_key][author]['commits'] = \
            self._authors_of_repository[author]['commits']

    def _update_merge_commit(self, repository, line) :
        splitted_line = line.split(' ')
        stamp = splitted_line[0]
        # meld stamp and repository into a single key
        stamp_key = ' '.join([stamp, repository])
        author = ' '.join(splitted_line[1:])
        if author not in self._authors_of_repository :
            self._authors_of_repository[author] = \
                {'lines_added' : 0, 'lines_removed' : 0, 'commits' : 0}
        self._authors_of_repository[author]['commits'] = \
            self._authors_of_repository[author].get('commits', 0) + 1
        if stamp_key not in self.changes_by_date_by_author :
            self.changes_by_date_by_author[stamp_key] = {}
        if author not in self.changes_by_date_by_author[stamp_key] :
            self.changes_by_date_by_author[stamp_key][author] = {}
        self.changes_by_date_by_author[stamp_key][author]['merge_commit'] = True
        self.changes_by_date_by_author[stamp_key][author]['lines_added'] = 0
        self.changes_by_date_by_author[stamp_key][author]['lines_removed'] = 0
        self.changes_by_date_by_author[stamp_key][author]['commits'] = \
            self._authors_of_repository[author]['commits']

# ****************************************************************************************
# ****************************************************************************************

class GitTagsData(GitStatisticsBase) :
    def __init__(self, conf, gitpaths) :
        super().__init__(conf, gitpaths)
        self.tags = {}

    def collect(self) :
        self.runstart_stamp = time.time()
        repo_names = []
        for gitpath in self.gitpaths :
            print(f"Git path: {gitpath}")
            prev_dir = os.getcwd()
            os.chdir(gitpath)
            print('Collecting data...')
            self._authors_of_repository = {}
            repository = os.path.basename(os.path.abspath(gitpath))
            repo_names.append(repository)
            self._collect_tags(repository)
            self._collect_tags_info(repository)
            os.chdir(prev_dir)
        if not self.configuration['project_name'] :
            self.configuration['project_name'] = ', '.join(repo_names)

    def _collect_tags(self, repository) :
        self.tags[repository] = {}
        tags = self.tags[repository]
        lines = get_pipe_output(['git show-ref --tags']).split('\n')
        for line in lines :
            if not line :
                continue
            (hash_value, tag) = line.split(' ')
            tag = tag.replace('refs/tags/', '')
            cmd = f"git log \"{hash_value}\" --pretty=format:\"%at %aN\" -n 1"
            output = get_pipe_output([cmd])
            if output :
                parts = output.split(' ')
                stamp = int(parts[0])
                date = datetime.datetime.fromtimestamp(stamp)
                tags[tag] = {
                    'stamp': stamp,
                    'hash' : hash_value,
                    'date' : date.strftime('%Y-%m-%d'),
                    'commits': 0,
                    'authors': {} }

    def _collect_tags_info(self, repository) :
        tags = self.tags[repository]
        tags_list = [(tagdetail['date'], tagname) for tagname, tagdetail in tags.items()]
        tags_sorted_by_date_desc = [tagname for *_, tagname in sorted(tags_list,reverse=True)]
        prev = None
        for tag in reversed(tags_sorted_by_date_desc):
            if prev is None:
                cmd = f"git shortlog -s \"{tag}\""
            else:
                cmd = f"git shortlog -s \"{tag}\" \"^{prev}\""
            output = get_pipe_output([cmd])
            if not output:
                continue
            prev = tag
            for line in output.split('\n'):
                parts = re.split(r'\s+', line, 2)
                commits = int(parts[1])
                author = parts[2]
                tags[tag]['commits'] += commits
                tags[tag]['authors'][author] = commits

# ****************************************************************************************
# ****************************************************************************************

class GitFilesStatistics(GitStatisticsBase) :
    def __init__(self, conf, gitpaths) :
        super().__init__(conf, gitpaths)
        self.total_size = 0
        self.total_files = 0
        self.extensions = {}
        self.files_by_stamp = {}
        self.lines_by_date_by_author = {}

    def get_total_size(self) :
        return self.total_size

    def get_total_files(self) :
        return self.total_files

    def get_extensions(self) :
        return self.extensions

    def get_files_by_stamp(self) :
        return self.files_by_stamp

    def get_lines_by_date_by_author(self) :
        return self.lines_by_date_by_author

    def collect(self) :
        self.runstart_stamp = time.time()
        repo_names = []
        for gitpath in self.gitpaths :
            print(f"Git path: {gitpath}")
            prev_dir = os.getcwd()
            os.chdir(gitpath)
            print('Collecting data...')
            self._authors_of_repository = {}
            repository = os.path.basename(os.path.abspath(gitpath))
            repo_names.append(repository)
            self._collect_files(repository)
            self._collect_revlist(repository)
            os.chdir(prev_dir)
        if not self.configuration['project_name'] :
            self.configuration['project_name'] = ', '.join(repo_names)

    def _collect_files(self, _repository) :
        cmd = f"git ls-tree -r -l {self.get_commit_range('HEAD', end_only=True)}"
        pipe_out = get_pipe_output([cmd])
        lines = pipe_out.split('\n')
        ext_blob = [el for el in map(self._add_ext_blob, lines) if el is not None]
        ext_lines = GitStatisticsParallel.ext_lines_by_blob(
            ext_blob, self.configuration['processes'])
        self._update_extensions(ext_lines)

    def _add_ext_blob(self, line) :
        if not line :
            return None
        parts = re.split(r'\s+', line, 4)
        if parts[0] == '160000' and parts[3] == '-' :
            # skip submodules
            return None
        blob_id = parts[2]
        filesize = int(parts[3])
        fullpath = parts[4]
        filename = fullpath.split('/')[-1]
        first_dot = filename.find('.')
        last_dot = filename.rfind('.')
        if first_dot == -1 or last_dot == 0 or \
           len(filename)-last_dot-1 > self.configuration['max_ext_length'] :
            ext = ''
        else :
            ext = filename[(last_dot+1):]
        self.total_size += filesize
        self.total_files += 1
        return (ext, blob_id)

    def _update_extensions(self, ext_lines) :
        for ext, lines in ext_lines :
            if ext not in self.extensions :
                self.extensions[ext] = {'files' : 0, 'lines' : 0}
            self.extensions[ext]['files'] += 1
            self.extensions[ext]['lines'] += lines

    def _collect_revlist(self, repository) :
        cmd = f"git rev-list --pretty=format:\"%at %T %H\" {self.get_log_range('HEAD')}"
        pipe_out = get_pipe_output([cmd, 'grep -v ^commit'])
        lines = pipe_out.strip().split('\n')
        # Outputs "<stamp> <revlist> <commit hash>"
        lines.reverse()
        time_files_commit = GitStatisticsParallel.file_tree_by_revlist(
            lines, self.configuration['processes'])
        self._update_files_by_stamp(repository, time_files_commit)
        if self.configuration['lines_by_date'] :
            lines_by_authors_by_stamp = self._lines_by_authors_by_stamp(time_files_commit)
            self._update_lines_by_date_by_author(repository, lines_by_authors_by_stamp)

    def _update_files_by_stamp(self, repository, time_files_commit) :
        prev_num_files = 0
        for timestamp, file_tree, _ in time_files_commit :
            # meld stamp and repository into a single key for self.files_by_stamp
            stamp_key = ' '.join([timestamp, repository])
            num_files = len(file_tree)
            if stamp_key not in self.files_by_stamp :
                self.files_by_stamp[stamp_key] = {}
            self.files_by_stamp[stamp_key]['files'] = num_files
            self.files_by_stamp[stamp_key]['delta_files'] = num_files - prev_num_files
            prev_num_files = num_files

    def _lines_by_authors_by_stamp(self, time_files_commit) :
        lines_by_authors = GitStatisticsParallel.lines_by_authors
        return [(timestamp, lines_by_authors(
            file_tree, commit_hash, self.configuration['processes']))
                for timestamp, file_tree, commit_hash in time_files_commit]

    def _update_lines_by_date_by_author(self, repository, lines_by_authors_by_stamp) :
        prev_lines_by_authors = Counter()
        for timestamp, lines_by_authors in lines_by_authors_by_stamp :
            # meld stamp and repository into a single key for self.files_by_stamp
            stamp_key = ' '.join([timestamp, repository])
            self.lines_by_date_by_author[stamp_key] = {}
            lines_by_date_by_author = self.lines_by_date_by_author[stamp_key]
            prev_authors = set(prev_lines_by_authors.keys())
            authors = set(lines_by_authors.keys())
            for author in authors.union(prev_authors) :
                lines_by_date_by_author[author] = {}
            for author in prev_authors.difference(authors) :
                lines_by_date_by_author[author]['lines'] = 0
                lines_by_date_by_author[author]['delta_lines'] = -prev_lines_by_authors[author]
            for author in authors.intersection(prev_authors) :
                lines_by_date_by_author[author]['lines'] = lines_by_authors[author]
                lines_by_date_by_author[author]['delta_lines'] = \
                    lines_by_authors[author] - prev_lines_by_authors[author]
            for author in authors.difference(prev_authors) :
                lines_by_date_by_author[author]['lines'] = lines_by_authors[author]
                lines_by_date_by_author[author]['delta_lines'] = lines_by_authors[author]
            prev_lines_by_authors = lines_by_authors

# ****************************************************************************************
# ****************************************************************************************

class GitContributionActivity(GitStatisticsBase) :
    def __init__(self, conf, gitpaths) :
        super().__init__(conf, gitpaths)
        self.first_commit_stamp = 0
        self.last_commit_stamp = 0
        self.total_commits = 0
        self.domains = {}
        self.activity_by_hour_of_day = {}
        self.activity_by_hour_of_day_busiest = 0
        self.activity_by_day_of_week = {}
        self.activity_by_hour_of_week = {}
        self.activity_by_hour_of_week_busiest = 0
        self.activity_by_month_of_year = {}
        self.activity_by_year_week = {}
        self.activity_by_year_week_peak = 0
        self.author_of_month = {}
        self.commits_by_month = {}
        self.author_of_year = {}
        self.commits_by_year = {}
        self.first_active_day = None
        self.active_days = set()
        self.commits_by_timezone = {}

    def get_first_commit_date(self) :
        return datetime.datetime.fromtimestamp(self.first_commit_stamp)

    def get_last_commit_date(self) :
        return datetime.datetime.fromtimestamp(self.last_commit_stamp)

    def get_commit_delta_days(self) :
        return (self.last_commit_stamp // 86400 - self.first_commit_stamp // 86400) + 1

    def get_active_days(self) :
        return self.active_days

    def get_total_commits(self) :
        return self.total_commits

    def get_activity_by_hour_of_day(self) :
        return self.activity_by_hour_of_day

    def get_activity_by_day_of_week(self) :
        return self.activity_by_day_of_week

    def get_activity_by_month_of_year(self) :
        return self.activity_by_month_of_year

    def get_commits_by_month(self) :
        return self.commits_by_month

    def get_commits_by_year(self) :
        return self.commits_by_year

    def get_domains_sorted_by_commits(self, **kwargs) :
        return sorted(self.domains.items(), key=lambda el : el[1]['commits'], **kwargs)

    def get_activity_by_hour_of_week(self) :
        return self.activity_by_hour_of_week

    def get_commits_by_timezone(self) :
        return self.commits_by_timezone

    def get_author_of_month(self) :
        return self.author_of_month

    def get_author_of_year(self) :
        return self.author_of_year

    def collect(self) :
        self.runstart_stamp = time.time()
        repo_names = []
        for gitpath in self.gitpaths :
            print(f"Git path: {gitpath}")
            prev_dir = os.getcwd()
            os.chdir(gitpath)
            print('Collecting data...')
            self._authors_of_repository = {}
            repository = os.path.basename(os.path.abspath(gitpath))
            repo_names.append(repository)
            self._collect_commits_graph(repository)
            os.chdir(prev_dir)
        if not self.configuration['project_name'] :
            self.configuration['project_name'] = ', '.join(repo_names)

    def _collect_commits_graph(self, _repository) :
        # Outputs "<stamp> <date> <time> <timezone> <author> '<' <mail> '>'"
        cmd = f"git rev-list --pretty=format:\"%at %ai %aN <%aE>\" {self.get_log_range('HEAD')}"
        pipe_out = get_pipe_output([cmd, 'grep -v ^commit'])
        lines = pipe_out.split('\n')
        self.total_commits += len(lines)
        for line in lines :
            parts = line.split(' ', 4)
            author = ''
            stamp = int(parts[0])
            date = datetime.datetime.fromtimestamp(stamp)
            timezone = parts[3]
            author, mail = parts[4].split('<', 1)
            author = author.rstrip()
            mail = mail.rstrip('>')
            domain = '?'
            if mail.find('@') != -1 :
                domain = mail.rsplit('@', 1)[1]

            self._update_extremal_commit_stamps(stamp)
            self._update_mail_domains(domain)
            self._update_activity(date)
            self._update_author_stats(author, stamp)
            self._update_author_activity(author, date)
            self._update_commits_by_month(author, date)
            self._update_commits_by_year(author, date)
            self._update_active_days(date)
            self._update_timezones(timezone)

    def _update_extremal_commit_stamps(self, stamp) :
        if stamp > self.last_commit_stamp :
            self.last_commit_stamp = stamp
        if self.first_commit_stamp == 0 or stamp < self.first_commit_stamp :
            self.first_commit_stamp = stamp

    def _update_mail_domains(self, domain) :
        if domain not in self.domains :
            self.domains[domain] = {}
        self.domains[domain]['commits'] = self.domains[domain].get('commits', 0) + 1

    def _update_activity(self, date) :
        hour = date.hour
        self.activity_by_hour_of_day[hour] = self.activity_by_hour_of_day.get(hour, 0) + 1
        if self.activity_by_hour_of_day[hour] > self.activity_by_hour_of_day_busiest :
            self.activity_by_hour_of_day_busiest = self.activity_by_hour_of_day[hour]

        day = date.weekday()
        self.activity_by_day_of_week[day] = self.activity_by_day_of_week.get(day, 0) + 1
        if day not in self.activity_by_hour_of_week :
            self.activity_by_hour_of_week[day] = {}
        self.activity_by_hour_of_week[day][hour] = \
            self.activity_by_hour_of_week[day].get(hour, 0) + 1
        if self.activity_by_hour_of_week[day][hour] > self.activity_by_hour_of_week_busiest :
            self.activity_by_hour_of_week_busiest = self.activity_by_hour_of_week[day][hour]

        month = date.month
        self.activity_by_month_of_year[month] = self.activity_by_month_of_year.get(month, 0) + 1

        yyw = date.strftime('%Y-%W')
        self.activity_by_year_week[yyw] = self.activity_by_year_week.get(yyw, 0) + 1
        if self.activity_by_year_week_peak < self.activity_by_year_week[yyw] :
            self.activity_by_year_week_peak = self.activity_by_year_week[yyw]

    def _update_author_stats(self, author, stamp) :
        if author not in self._authors_of_repository :
            self._authors_of_repository[author] = {}
        # commits, note again that commits may be in any date order
        # because of cherry-picking and patches
        if 'last_commit_stamp' not in self._authors_of_repository[author] :
            self._authors_of_repository[author]['last_commit_stamp'] = stamp
        if stamp > self._authors_of_repository[author]['last_commit_stamp'] :
            self._authors_of_repository[author]['last_commit_stamp'] = stamp
        if 'first_commit_stamp' not in self._authors_of_repository[author] :
            self._authors_of_repository[author]['first_commit_stamp'] = stamp
        if stamp < self._authors_of_repository[author]['first_commit_stamp'] :
            self._authors_of_repository[author]['first_commit_stamp'] = stamp

    def _update_author_activity(self, author, date) :
        yymmdd = date.strftime('%Y-%m-%d')
        if 'first_active_day' not in self._authors_of_repository[author] :
            self._authors_of_repository[author]['first_active_day'] = yymmdd
        if yymmdd < self._authors_of_repository[author]['first_active_day'] :
            self._authors_of_repository[author]['first_active_day'] = yymmdd
        if 'active_days' not in self._authors_of_repository[author] :
            self._authors_of_repository[author]['active_days'] = set([yymmdd])
        self._authors_of_repository[author]['active_days'].add(yymmdd)

    def _update_commits_by_month(self, author, date) :
        yymm = date.strftime('%Y-%m')
        if yymm in self.author_of_month :
            self.author_of_month[yymm][author] = self.author_of_month[yymm].get(author, 0) + 1
        else :
            self.author_of_month[yymm] = {}
            self.author_of_month[yymm][author] = 1
        self.commits_by_month[yymm] = self.commits_by_month.get(yymm, 0) + 1

    def _update_commits_by_year(self, author, date) :
        year = date.year
        if year in self.author_of_year :
            self.author_of_year[year][author] = self.author_of_year[year].get(author, 0) + 1
        else :
            self.author_of_year[year] = {}
            self.author_of_year[year][author] = 1
        self.commits_by_year[year] = self.commits_by_year.get(year, 0) + 1

    def _update_active_days(self, date) :
        yymmdd = date.strftime('%Y-%m-%d')
        if self.first_active_day is None :
            self.first_active_day = yymmdd
        if yymmdd < self.first_active_day :
            self.first_active_day = yymmdd
        self.active_days.add(yymmdd)

    def _update_timezones(self, timezone) :
        self.commits_by_timezone[timezone] = self.commits_by_timezone.get(timezone, 0) + 1

# ****************************************************************************************
# ****************************************************************************************

class GitStatisticsData(LogShortStatData,
                        GitTagsData,
                        GitFilesStatistics,
                        GitContributionActivity) :
    def __init__(self, conf, gitpaths) :
        super().__init__(conf, gitpaths)
        self.total_authors = set()
        self.authors = {}

    def get_total_authors(self) :
        return self.total_authors

    def get_authors(self, limit=None) :
        authors_by_commits = [
            author for author, _ in
            sorted(self.authors.items(), key=lambda el : el[1]['commits'], reverse=True)]
        return authors_by_commits[:limit]

    def collect(self) :
        self.runstart_stamp = time.time()
        repo_names = []
        for gitpath in self.gitpaths :
            print(f"Git path: {gitpath}")
            prev_dir = os.getcwd()
            os.chdir(gitpath)
            print('Collecting data...')
            self._authors_of_repository = {}
            repository = os.path.basename(os.path.abspath(gitpath))
            repo_names.append(repository)
            self._collect_authors(repository)
            self._collect_tags(repository)
            self._collect_tags_info(repository)
            self._collect_commits_graph(repository)
            self._collect_files(repository)
            self._collect_lines_modified(repository)
            self._collect_lines_modified_by_author(repository)
            self._collect_revlist(repository)
            self._update_and_accumulate_authors_stats()
            os.chdir(prev_dir)
        if not self.configuration['project_name'] :
            self.configuration['project_name'] = ', '.join(repo_names)

    def _collect_authors(self, _repository) :
        cmd = f"git shortlog -s {self.get_log_range()}"
        pipe_out = get_pipe_output([cmd, 'cut -c8-'])
        lines = pipe_out.split('\n')
        self.total_authors.update(lines)

    def _update_and_accumulate_authors_stats(self) :
        for author, stats in self._authors_of_repository.items() :
            self._update_and_accumulate_from(author, stats)

    def _update_and_accumulate_from(self, author, stats) :
        if author not in self.authors :
            self.authors[author] = stats.copy()
        else :
            author = self.authors[author]
            author['last_commit_stamp'] = \
                max((author['last_commit_stamp'], stats['last_commit_stamp']))
            author['first_commit_stamp'] = \
                min((author['first_commit_stamp'], stats['first_commit_stamp']))
            author['first_active_day'] = \
                min((author['first_active_day'], stats['first_active_day']))
            author['active_days'].update(stats['active_days'])
            author['commits'] += stats['commits']
            author['lines_added'] += stats['lines_added']
            author['lines_removed'] += stats['lines_removed']

class GitStatisticsWriter :
    def __init__(self, git_statistics) :
        self.git_statistics = git_statistics

    def write(self, outputpath) :
        prev_dir = os.getcwd()
        os.chdir(outputpath)
        self.write_hour_of_day()
        self.write_day_of_week()
        self.write_month_of_year()
        self.write_commits_by_year_month()
        self.write_commits_by_year()
        self.write_lines_and_commits_by_author()
        self.write_domains()
        self.write_lines_of_code()
        self.write_files_by_date()
        self.write_lines_of_code_by_author()
        os.chdir(prev_dir)

    def write_hour_of_day(self) :
        with open('hour_of_day.csv', 'w', encoding='utf-8') as outputfile :
            outputfile.write('Hour, Commits\n')
            activity_by_hour_of_day = self.git_statistics.get_activity_by_hour_of_day()
            for i in range(0, 24) :
                outputfile.write(f"{i}, {activity_by_hour_of_day.get(i, 0)}\n")

    def write_day_of_week(self) :
        with open('day_of_week.csv', 'w', encoding='utf-8') as outputfile :
            outputfile.write('Weekday, Commits\n')
            activity_by_day_of_week = self.git_statistics.get_activity_by_day_of_week()
            for i, weekday in enumerate(calendar.day_abbr) :
                outputfile.write(f"{weekday}, {activity_by_day_of_week.get(i, 0)}\n")

    def write_month_of_year(self) :
        with open('month_of_year.csv', 'w', encoding='utf-8') as outputfile :
            outputfile.write('Month, Commits\n')
            activity_by_month_of_year = self.git_statistics.get_activity_by_month_of_year()
            for i, _ in enumerate(calendar.month_name[1:], 1) :
                outputfile.write(f"{i}, {activity_by_month_of_year.get(i, 0)}\n")

    def write_commits_by_year_month(self) :
        with open('commits_by_year_month.csv', 'w', encoding='utf-8') as outputfile :
            outputfile.write('Year-Month, Commits\n')
            commits_by_month = self.git_statistics.get_commits_by_month()
            for yymm in sorted(commits_by_month.keys()) :
                outputfile.write(f"{yymm}, {commits_by_month[yymm]}\n")

    def write_commits_by_year(self) :
        with open('commits_by_year.csv', 'w', encoding='utf-8') as outputfile :
            outputfile.write('Year, Commits\n')
            commits_by_year = self.git_statistics.get_commits_by_year()
            for year in sorted(commits_by_year.keys()) :
                outputfile.write(f"{year}, {commits_by_year[year]}\n")

    def write_lines_and_commits_by_author(self) :
        lines_added_by_authors = {}
        commits_by_authors = {}
        limit = self.git_statistics.configuration['max_authors']
        authors_to_write = self.git_statistics.get_authors(limit)
        for author in authors_to_write :
            lines_added_by_authors[author] = 0
            commits_by_authors[author] = 0
        with open('lines_of_code_added_by_author.csv', 'w', encoding='utf-8') as outputfile1, \
             open('commits_by_author.csv', 'w', encoding='utf-8') as outputfile2 :
            changes_by_date_by_author = self.git_statistics.get_changes_by_date_by_author()
            outputfile1.write('Stamp, ' + ', '.join(authors_to_write) + '\n')
            outputfile2.write('Stamp, ' + ', '.join(authors_to_write) + '\n')
            for stamp_key in sorted(changes_by_date_by_author.keys()) :
                # structure of stamp_key
                # stamp repository
                stamp = stamp_key.split()[0]
                outputfile1.write(f"{stamp}, ")
                outputfile2.write(f"{stamp}, ")
                for author in set(changes_by_date_by_author[stamp_key].keys()).intersection(
                        authors_to_write) :
                    lines_added_by_authors[author] += \
                        changes_by_date_by_author[stamp_key][author]['lines_added']
                    commits_by_authors[author] += 1
                outputfile1.write(', '.join(map(str, lines_added_by_authors.values())))
                outputfile2.write(', '.join(map(str, commits_by_authors.values())))
                outputfile1.write('\n')
                outputfile2.write('\n')

    def write_domains(self) :
        domains = self.git_statistics.get_domains_sorted_by_commits(reverse=True)
        with open('domains.csv', 'w', encoding='utf-8') as outputfile :
            outputfile.write('Domain, Ranking, Commits\n')
            for i, domain_info in enumerate(domains, 1) :
                domain, info = domain_info
                if i > self.git_statistics.configuration['max_domains'] :
                    break
                outputfile.write(f"{domain}, {i}, {info['commits']}\n")

    def write_lines_of_code(self) :
        changes_by_date = self.git_statistics.get_changes_by_date()
        with open('lines_of_code.csv', 'w', encoding='utf-8') as outputfile :
            total_lines = 0
            outputfile.write('Timestamp, Total Lines\n')
            for stamp_key in sorted(changes_by_date.keys()) :
                # structure of stamp_key
                # stamp repository
                stamp = stamp_key.split()[0]
                total_lines += changes_by_date[stamp_key]['inserted']
                total_lines -= changes_by_date[stamp_key]['deleted']
                outputfile.write(f"{stamp}, {total_lines}\n")

    def write_files_by_date(self) :
        files_by_stamp = self.git_statistics.get_files_by_stamp()
        total_files = 0
        with open('files_by_date.csv', 'w', encoding='utf-8') as outputfile :
            outputfile.write('Timestamp, Total files\n')
            for stamp_key in sorted(files_by_stamp.keys()) :
                # structure of stamp_key
                # stamp repository
                stamp = stamp_key.split()[0]
                total_files += files_by_stamp[stamp_key]['delta_files']
                outputfile.write(f"{stamp}, {total_files}\n")

    def write_lines_of_code_by_author(self) :
        if not self.git_statistics.configuration['lines_by_date'] :
            return
        lines_by_authors = {}
        limit = self.git_statistics.configuration['max_authors']
        authors_to_write = self.git_statistics.get_authors(limit)
        for author in authors_to_write :
            lines_by_authors[author] = 0
        with open('lines_of_code_by_author.csv', 'w', encoding='utf-8') as outputfile :
            lines_by_date_by_author = self.git_statistics.get_lines_by_date_by_author()
            outputfile.write('Stamp, ' + ', '.join(authors_to_write) + '\n')
            for stamp_key in sorted(lines_by_date_by_author.keys()) :
                # structure of stamp_key
                # stamp repository
                stamp = stamp_key.split()[0]
                outputfile.write(f"{stamp}, ")
                for author in set(lines_by_date_by_author[stamp_key].keys()).intersection(
                        authors_to_write) :
                    lines_by_authors[author] += \
                        lines_by_date_by_author[stamp_key][author]['delta_lines']
                outputfile.write(', '.join(map(str, lines_by_authors.values())))
                outputfile.write('\n')

def main(args_orig) :
    time_start = time.time()
    conf = {
        'max_domains': 10,
        'max_ext_length': 10,
        'style': 'gitstats.css',
        'max_authors': 20,
        'authors_top': 5,
        'commit_begin': '',
        'commit_end': 'HEAD',
        'linear_linestats': 1,
        'project_name': '',
        'processes': 8,
        'start_date': '',
        'lines_by_date': 0,
    }
    def usage() :
        print(f"""
Usage gitstats2_collect_data.py [options] <gitpath..> <outputpath>

Options:
-c key=value         Override configuration value

Default config values:
{conf}

Please see the manual page for more details.""")

    optlist, args = getopt.getopt(args_orig, 'hc:', ["help"])
    for flag, val in optlist :
        if flag == '-c' :
            key, value = val.split('=', 1)
            if key not in conf :
                raise KeyError(f"No such key \"{key}\" in config")
            if isinstance(conf[key], int) :
                conf[key] = int(value)
            else :
                conf[key] = value
        elif flag in ('h', '--help') :
            usage()
            sys.exit()
    if len(args) < 2 :
        usage()
        sys.exit(0)

    gitpaths = args[0:-1]
    outputpath = os.path.abspath(args[-1])

    try :
        os.makedirs(outputpath)
    except OSError :
        pass
    if not os.path.isdir(outputpath) :
        print("FATAL: Output path is not a directory or does not exist")
        sys.exit(1)

    git_statistics = GitStatisticsData(conf, gitpaths)
    git_statistics.collect()
    statistics_writer = GitStatisticsWriter(git_statistics)
    statistics_writer.write(outputpath)

    time_end = time.time()
    exectime_total = time_end - time_start
    print(f"Execution time {exectime_total:.5f} secs, {get_pipe_output.exectime_commands:.5f} secs \
({(get_pipe_output.exectime_commands/exectime_total):.2%}) in external commands")

if __name__ == '__main__' :
    main(sys.argv[1:])
