# -*- python-indent-offset: 4 -*-
import sys
import getopt
import os
import subprocess
import time
import datetime
import re
import calendar
from collections import namedtuple

if sys.version_info < (3, 6) :
    print("Python 3.6 or higher is required for gitstats2", file=sys.stderr)
    sys.exit(1)

class GitStatisticsData :
    def __init__(self, conf, gitpaths) :
        self.configuration = conf.copy()
        self._gitpaths = gitpaths
        self.runstart_stamp = float(0.0)
        self.first_commit_stamp = 0
        self.last_commit_stamp = 0
        self.total_files = 0
        self.total_lines = 0
        self.total_lines_added = 0
        self.total_lines_removed = 0
        self.total_commits = 0
        self.total_authors = set()
        self.exectime_commands = float(0.0)
        self.tags = {}
        self.domains = {}
        self.activity_by_hour_of_day = {}
        self.activity_by_hour_of_day_busiest = 0
        self.activity_by_day_of_week = {}
        self.activity_by_hour_of_week = {}
        self.activity_by_hour_of_week_busiest = 0
        self.activity_by_month_of_year = {}
        self.activity_by_year_week = {}
        self.activity_by_year_week_peak = 0
        self.authors = {}
        self._authors_of_repository = {}
        self.author_of_month = {}
        self.commits_by_month = {}
        self.author_of_year = {}
        self.commits_by_year = {}
        self.first_active_day = None
        self.active_days = set()
        self.commits_by_timezone = {}
        self.total_size = 0
        self.extensions = {}
        self.lines_added_by_month = {}
        self.lines_removed_by_month = {}
        self.lines_added_by_year = {}
        self.lines_removed_by_year = {}
        self.changes_by_date_by_author = {}
        self.changes_by_date = {}

    def reset(self) :
        self.runstart_stamp = float(0.0)
        self.first_commit_stamp = 0
        self.last_commit_stamp = 0
        self.total_files = 0
        self.total_lines = 0
        self.total_lines_added = 0
        self.total_lines_removed = 0
        self.total_commits = 0
        self.total_authors = set()
        self.exectime_commands = float(0.0)
        self.tags = {}
        self.domains = {}
        self.activity_by_hour_of_day = {}
        self.activity_by_hour_of_day_busiest = 0
        self.activity_by_day_of_week = {}
        self.activity_by_hour_of_week = {}
        self.activity_by_hour_of_week_busiest = 0
        self.activity_by_month_of_year = {}
        self.activity_by_year_week = {}
        self.activity_by_year_week_peak = 0
        self.authors = {}
        self._authors_of_repository = {}
        self.author_of_month = {}
        self.commits_by_month = {}
        self.author_of_year = {}
        self.commits_by_year = {}
        self.first_active_day = None
        self.active_days = set()
        self.commits_by_timezone = {}
        self.total_size = 0
        self.extensions = {}
        self.lines_added_by_month = {}
        self.lines_removed_by_month = {}
        self.lines_added_by_year = {}
        self.lines_removed_by_year = {}
        self.changes_by_date_by_author = {}
        self.changes_by_date = {}

    def get_runstart_stamp(self) :
        return self.runstart_stamp

    def get_gitstats2_version(self) :
        gitstats_repo = os.path.dirname(os.path.abspath(__file__))
        commit_range = '@'
        cmd = f"git --git-dir={gitstats_repo}/.git --work-tree={gitstats_repo} \
rev-parse --short {commit_range}"
        return self._get_pipe_output([cmd])

    def get_git_version(self) :
        return self._get_pipe_output(['git --version'])

    def get_first_commit_date(self) :
        return datetime.datetime.fromtimestamp(self.first_commit_stamp)

    def get_last_commit_date(self) :
        return datetime.datetime.fromtimestamp(self.last_commit_stamp)

    def get_commit_delta_days(self) :
        return (self.last_commit_stamp // 86400 - self.first_commit_stamp // 86400) + 1

    def get_active_days(self) :
        return self.active_days

    def get_total_files(self) :
        return self.total_files

    def get_total_lines_of_code(self) :
        return self.total_lines

    def get_total_lines_added(self) :
        return self.total_lines_added

    def get_total_lines_removed(self) :
        return self.total_lines_removed

    def get_total_commits(self) :
        return self.total_commits

    def get_total_authors(self) :
        return self.total_authors

    def get_exectime_commands(self) :
        return self.exectime_commands

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

    def get_changes_by_date_by_author(self) :
        return self.changes_by_date_by_author

    def get_authors(self, limit=None) :
        res = self._get_keys_sorted_by_value_key(self.authors, 'commits')
        res.reverse()
        return res[:limit]

    def get_domains_by_commits(self) :
        return self._get_keys_sorted_by_value_key(self.domains, 'commits')

    def get_domain_info(self, domain) :
        return self.domains[domain]

    def get_changes_by_date(self) :
        return self.changes_by_date

    def collect(self) :
        self.runstart_stamp = time.time()
        repo_names = []
        for gitpath in self._gitpaths :
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
            self._collect_revlist(repository)
            self._collect_files(repository)
            self._collect_lines_modified(repository)
            self._collect_lines_modified_by_author(repository)
            self._update_and_accumulate_authors_stats()
            os.chdir(prev_dir)
        if not self.configuration['project_name'] :
            self.configuration['project_name'] = ', '.join(repo_names)

    def _get_pipe_output(self, cmds, quiet=False) :
        start = time.time()
        if not quiet and os.isatty(1) :
            print('>> ' + ' | '.join(cmds), end=' ')
            sys.stdout.flush()
        process = subprocess.Popen(
            cmds[0],
            stdout = subprocess.PIPE,
            shell = True,
            encoding = 'utf8')
        processes=[process]
        for command in cmds[1:] :
            process = subprocess.Popen(
                command,
                stdin = process.stdout,
                stdout = subprocess.PIPE,
                shell = True,
                encoding = 'utf8')
            processes.append(process)
        output = process.communicate()[0]
        for process in processes:
            process.wait()
        end = time.time()
        if not quiet :
            if os.isatty(1) :
                print('\r', end=' ')
            print(f"[{(end-start):.5f}] >> {' | '.join(cmds)}")
        self.exectime_commands += (end - start)
        return output.rstrip('\n')

    def _get_log_range(self, default_range='HEAD', end_only=True) :
        commit_range = self._get_commit_range(default_range, end_only)
        if self.configuration['start_date'] :
            return f"--since=\"{self.configuration['start_date']}\" \"{commit_range}\""
        return commit_range

    def _get_commit_range(self, default_range='HEAD', end_only=True) :
        if self.configuration['commit_end'] :
            if end_only or not self.configuration['commit_begin'] :
                return self.configuration['commit_end']
            return f"{self.configuration['commit_begin']}..{self.configuration['commit_end']}"
        return default_range

    @staticmethod
    def _get_modified_counts(line) :
        numbers = tuple(map(int, re.findall(r'\d+', line)))
        mod_counts_tuple = namedtuple('ModCounts', 'files inserted deleted')
        if len(numbers) == 1 :
            modification_counts = mod_counts_tuple(numbers[0], inserted=0, deleted=0)
        elif len(numbers) == 2 and line.find('(+)') != -1 :
            modification_counts = mod_counts_tuple(numbers[0], inserted=numbers[1], deleted=0)
        elif len(numbers) == 2 and line.find('(-)') != -1 :
            modification_counts = mod_counts_tuple(numbers[0], inserted=0, deleted=numbers[1])
        else :
            modification_counts = mod_counts_tuple(numbers[0], inserted=numbers[1], deleted=numbers[2])
        return modification_counts

    @staticmethod
    def _get_keys_sorted_by_value_key(input_dict, key) :
        by_value_key_list = [(input_dict[el][key], el) for el in input_dict.keys()]
        return [el for *_, el in sorted(by_value_key_list)]

    def _collect_authors(self, _repository) :
        cmd = f"git shortlog -s {self._get_log_range()}"
        pipe_out = self._get_pipe_output([cmd, 'cut -c8-'])
        lines = pipe_out.split('\n')
        self.total_authors.update(lines)

    def _collect_tags(self, repository) :
        self.tags[repository] = {}
        tags = self.tags[repository]
        lines = self._get_pipe_output(['git show-ref --tags']).split('\n')
        for line in lines :
            if not line :
                continue
            (hash_value, tag) = line.split(' ')
            tag = tag.replace('refs/tags/', '')
            cmd = f"git log \"{hash_value}\" --pretty=format:\"%at %aN\" -n 1"
            output = self._get_pipe_output([cmd])
            if output :
                parts = output.split(' ')
                stamp = 0
                try :
                    stamp = int(parts[0])
                except ValueError :
                    stamp = 0
                tags[tag] = {
                    'stamp': stamp,
                    'hash' : hash_value,
                    'date' : datetime.datetime.fromtimestamp(stamp).strftime('%Y-%m-%d'),
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
            output = self._get_pipe_output([cmd])
            if not output:
                continue
            prev = tag
            for line in output.split('\n'):
                parts = re.split(r'\s+', line, 2)
                commits = int(parts[1])
                author = parts[2]
                tags[tag]['commits'] += commits
                tags[tag]['authors'][author] = commits

    def _collect_revlist(self, _repository) :
        # Outputs "<stamp> <date> <time> <timezone> <author> '<' <mail> '>'"
        cmd = f"git rev-list --pretty=format:\"%at %ai %aN <%aE>\" {self._get_log_range('HEAD')}"
        pipe_out = self._get_pipe_output([cmd, 'grep -v ^commit'])
        lines = pipe_out.split('\n')
        self.total_commits += len(lines)
        for line in lines :
            parts = line.split(' ', 4)
            author = ''
            try :
                stamp = int(parts[0])
            except ValueError :
                stamp = 0
            timezone = parts[3]
            author, mail = parts[4].split('<', 1)
            author = author.rstrip()
            mail = mail.rstrip('>')
            domain = '?'
            if mail.find('@') != -1 :
                domain = mail.rsplit('@', 1)[1]
            date = datetime.datetime.fromtimestamp(float(stamp))

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
        if self.first_active_day == None :
            self.first_active_day = yymmdd
        if yymmdd < self.first_active_day :
            self.first_active_day = yymmdd
        self.active_days.add(yymmdd)

    def _update_timezones(self, timezone) :
        self.commits_by_timezone[timezone] = self.commits_by_timezone.get(timezone, 0) + 1

    def _collect_files(self, _repository) :
        cmd = f"git ls-tree -r -l -z {self._get_commit_range('HEAD', end_only=True)}"
        pipe_out = self._get_pipe_output([cmd])
        lines = pipe_out.split('\000')
        # blobs_to_read = []
        for line in lines :
            if not line :
                continue
            parts = re.split(r'\s+', line, 4)
            if parts[0] == '160000' and parts[3] == '-' :
                # skip submodules
                continue
            # blob_id = parts[2]
            filesize = int(parts[3])
            fullpath = parts[4]
            filename = fullpath.split('/')[-1]
            if filename.find('.') == -1 or filename.rfind('.') == 0 :
                ext = ''
            else :
                ext = filename[(filename.rfind('.')+1):]
            if len(ext) > self.configuration['max_ext_length'] :
                ext = ''
            if ext not in self.extensions :
                self.extensions[ext] = {'files' : 0,  'lines' : 0}
            self.extensions[ext]['files'] += 1

            self.total_size += filesize
            self.total_files += 1

    def _collect_lines_modified(self, repository) :
        extra = ''
        if self.configuration['linear_linestats'] :
            extra = '--first-parent -m'
        cmd = f"git log --shortstat {extra} --pretty=format:\"%at %aN\" \
{self._get_log_range('HEAD')}"
        pipe_out = self._get_pipe_output([cmd])
        lines = pipe_out.split('\n')
        lines.reverse()
        # outputs:
        #  N files changed, N insertions (+), N deletions(-)
        # <stamp> <author>
        files = 0
        inserted = 0
        deleted = 0
        total_lines = 0
        for line in lines :
            if not line :
                continue
            if re.search('files? changed', line) is not None :
                modified_counts = self._get_modified_counts(line)
                if len(modified_counts) == 3 :
                    (files, inserted, deleted) = modified_counts
                    total_lines += inserted
                    total_lines -= deleted
                    self.total_lines_added += inserted
                    self.total_lines_removed += deleted
                else :
                    print(f"Warning: failed to handle line \"{line}\"")
                    files = 0
                    inserted = 0
                    deleted = 0
            else :
                first_space = line.find(' ')
                if first_space != -1 :
                    try :
                        stamp = line[:first_space]
                        # meld stamp and repository into a single key for self.changes_by_date
                        stamp_key = ' '.join([stamp, repository])
                        self.changes_by_date[stamp_key] = {
                            'files' : files,
                            'inserted' : inserted,
                            'deleted' : deleted,
                            'lines' : total_lines }
                        date = datetime.datetime.fromtimestamp(int(stamp))
                        self._update_lines_modified_by_month(date, inserted, deleted)
                        self._update_lines_modified_by_year(date, inserted, deleted)
                        files = 0
                        inserted = 0
                        deleted = 0
                    except ValueError :
                        print(f"Warning: unexpected line \"{line}\"")
                else :
                    print(f"Warning unexpected line \"{line}\"")
        self.total_lines += total_lines

    def _update_lines_modified_by_month(self, date, inserted, deleted) :
        yymm = date.strftime('%Y-%m')
        self.lines_added_by_month[yymm] = self.lines_added_by_month.get(yymm, 0) + inserted
        self.lines_removed_by_month[yymm] = self.lines_removed_by_month.get(yymm, 0) + deleted

    def _update_lines_modified_by_year(self, date, inserted, deleted) :
        year = date.year
        self.lines_added_by_year[year] = self.lines_added_by_year.get(year, 0) + inserted
        self.lines_removed_by_year[year] = self.lines_removed_by_year.get(year, 0) + deleted

    def _collect_lines_modified_by_author(self, repository) :
        # Similar to _collect_lines_modified, but never use --first-parent
        # (we need to walk through every commit to know who
        # committed what, not just through mainline)
        cmd = f"git log --shortstat --date-order --pretty=format:\"%at %aN\" \
{self._get_log_range('@')}"
        pipe_out = self._get_pipe_output([cmd])
        lines = pipe_out.split('\n')
        lines.reverse()
        inserted = 0
        deleted = 0
        stamp = 0
        for line in lines :
            if not line :
                continue
            if re.search('files? changed', line) is not None :
                modified_counts = self._get_modified_counts(line)
                if len(modified_counts) == 3 :
                    (_files, inserted, deleted) = modified_counts
                else :
                    print(f"Warning: failed to handle line \"{line}\"")
                    inserted = 0
                    deleted = 0
            else :
                first_space = line.find(' ')
                if first_space != -1 :
                    try :
                        oldstamp = stamp
                        (stamp, author) = (int(line[:first_space]), line[first_space+1:])
                        if oldstamp > stamp :
                            # clock skew, keep old timestamp to avoid having ugly graph
                            stamp = oldstamp
                        # meld stamp and repository into a single key for self.changes_by_date_by_author
                        stamp_key = ' '.join([str(stamp), repository])
                        self._update_lines_modified_by_author(author, stamp_key, inserted, deleted)
                        inserted = 0
                        deleted = 0
                    except ValueError :
                        print(f"Warning: unexpectd line \"{line}\"")
                else :
                    print(f"Warning: unexpected line \"{line}\"")

    def _update_lines_modified_by_author(self, author, stamp_key, inserted, deleted) :
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
        domains_by_commits = self.git_statistics.get_domains_by_commits()
        domains_by_commits.reverse()
        with open('domains.csv', 'w', encoding='utf-8') as outputfile :
            outputfile.write('Domain, Ranking, Commits\n')
            for i, domain in enumerate(domains_by_commits, 1) :
                if i > self.git_statistics.configuration['max_domains'] :
                    break
                domain_info = self.git_statistics.get_domain_info(domain)
                outputfile.write(f"{domain}, {i}, {domain_info['commits']}\n")

    def write_lines_of_code(self) :
        changes_by_date = self.git_statistics.get_changes_by_date()
        with open('lines_of_code.csv', 'w', encoding='utf-8') as outputfile :
            total_lines = 0
            outputfile.write('Timestamp, TotalLines\n')
            for stamp_key in sorted(changes_by_date.keys()) :
                # structure of stamp_key
                # stamp repository
                stamp = stamp_key.split()[0]
                total_lines += changes_by_date[stamp_key]['inserted']
                total_lines -= changes_by_date[stamp_key]['deleted']
                outputfile.write(f"{stamp}, {total_lines}\n")

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
        'start_date': ''
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
    exectime_commands = git_statistics.get_exectime_commands()
    print(f"Execution time {exectime_total:.5f} secs, {exectime_commands:.5f} secs \
({(100.0*exectime_commands/exectime_total):.2f} %) in external commands")

if __name__ == '__main__' :
    main(sys.argv[1:])
