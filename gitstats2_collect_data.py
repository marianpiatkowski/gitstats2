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

class GitStatisticsData :
    def __init__(self, conf, gitpaths, outputpath) :
        self.configuration = conf.copy()
        self._gitpaths = gitpaths
        self._outputpath = outputpath
        self.runstart_stamp = float(0.0)
        self.first_commit_stamp = 0
        self.last_commit_stamp = 0
        self.active_days = set()
        self.total_files = 0
        self.total_lines = 0
        self.total_lines_added = 0
        self.total_lines_removed = 0
        self.total_commits = 0
        self.total_authors = 0
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
        self.author_of_month = {}
        self.commits_by_month = {}
        self.author_of_year = {}
        self.commits_by_year = {}
        self.last_active_day = None
        self.active_days = set()
        self.commits_by_timezone = {}
        self.total_size = 0
        self.extensions = {}
        self.lines_added_by_month = {}
        self.lines_removed_by_month = {}
        self.lines_added_by_year = {}
        self.lines_removed_by_year = {}
        self.changes_by_date_by_author = {}

    def reset(self) :
        self.runstart_stamp = float(0.0)
        self.first_commit_stamp = 0
        self.last_commit_stamp = 0
        self.active_days = set()
        self.total_files = 0
        self.total_lines = 0
        self.total_lines_added = 0
        self.total_lines_removed = 0
        self.total_commits = 0
        self.total_authors = 0
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
        self.author_of_month = {}
        self.commits_by_month = {}
        self.author_of_year = {}
        self.commits_by_year = {}
        self.last_active_day = None
        self.active_days = set()
        self.commits_by_timezone = {}
        self.total_size = 0
        self.extensions = {}
        self.lines_added_by_month = {}
        self.lines_removed_by_month = {}
        self.lines_added_by_year = {}
        self.lines_removed_by_year = {}
        self.changes_by_date_by_author = {}

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

    def collect(self) :
        self.runstart_stamp = time.time()
        if not self.configuration['project_name'] :
            self._concat_project_name()
        for gitpath in self._gitpaths :
            print(f"Git path: {gitpath}")
            prev_dir = os.getcwd()
            os.chdir(gitpath)
            print('Collecting data...')
            self._collect_authors()
            self._collect_tags()
            self._collect_revlist()
            self._collect_files()
            self._collect_lines_modified()
            self._collect_lines_modified_by_author()
            os.chdir(prev_dir)

    def write(self) :
        prev_dir = os.getcwd()
        os.chdir(self._outputpath)
        self._write_hour_of_day()
        self._write_day_of_week()
        self._write_month_of_year()
        self._write_commits_by_year_month()
        self._write_commits_by_year()
        os.chdir(prev_dir)

    def _concat_project_name(self) :
        git_repo_names = \
            list(map(lambda el : os.path.basename(os.path.abspath(el)), self._gitpaths))
        self.configuration['project_name'] = ', '.join(git_repo_names)

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

    def _collect_authors(self) :
        cmd = f"git shortlog -s {self._get_log_range()}"
        pipe_out = self._get_pipe_output([cmd, 'wc -l'])
        self.total_authors += int(pipe_out)

    def _collect_tags(self) :
        lines = self._get_pipe_output(['git show-ref --tags']).split('\n')
        tags = {}
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
        self._update_tags_info(tags)

    def _update_tags_info(self, tags) :
        self.tags.update(tags)
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
                self.tags[tag]['commits'] += commits
                self.tags[tag]['authors'][author] = commits

    def _collect_revlist(self) :
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
        if author not in self.authors :
            self.authors[author] = {}
        # commits, note again that commits may be in any date order
        # because of cherry-picking and patches
        if 'last_commit_stamp' not in self.authors[author] :
            self.authors[author]['last_commit_stamp'] = stamp
        if stamp > self.authors[author]['last_commit_stamp'] :
            self.authors[author]['last_commit_stamp'] = stamp
        if 'first_commit_stamp' not in self.authors[author] :
            self.authors[author]['first_commit_stamp'] = stamp
        if stamp < self.authors[author]['first_commit_stamp'] :
            self.authors[author]['first_commit_stamp'] = stamp

    def _update_author_activity(self, author, date) :
        yymmdd = date.strftime('%Y-%m-%d')
        if 'last_active_day' not in self.authors[author] :
            self.authors[author]['last_active_day'] = yymmdd
            self.authors[author]['active_days'] = set([yymmdd])
        elif yymmdd != self.authors[author]['last_active_day'] :
            self.authors[author]['last_active_day'] = yymmdd
            self.authors[author]['active_days'].add(yymmdd)

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
        if yymmdd != self.last_active_day :
            self.last_active_day = yymmdd
            self.active_days.add(yymmdd)

    def _update_timezones(self, timezone) :
        self.commits_by_timezone[timezone] = self.commits_by_timezone.get(timezone, 0) + 1

    def _collect_files(self) :
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

    def _collect_lines_modified(self) :
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
        inserted = 0
        deleted = 0
        total_lines = 0
        for line in lines :
            if not line :
                continue
            if re.search('files? changed', line) is not None :
                modified_counts = self._get_modified_counts(line)
                if len(modified_counts) == 3 :
                    (_files, inserted, deleted) = modified_counts
                    total_lines += inserted
                    total_lines -= deleted
                    self.total_lines_added += inserted
                    self.total_lines_removed += deleted
                else :
                    print(f"Warning: failed to handle line \"{line}\"")
                    inserted = 0
                    deleted = 0
            else :
                first_space = line.find(' ')
                if first_space != -1 :
                    try :
                        stamp = int(line[:first_space])
                        date = datetime.datetime.fromtimestamp(stamp)
                        self._update_lines_modified_by_month(date, inserted, deleted)
                        self._update_lines_modified_by_year(date, inserted, deleted)
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

    def _collect_lines_modified_by_author(self) :
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
                        self._update_lines_modified_by_author(author, stamp, inserted, deleted)
                        inserted = 0
                        deleted = 0
                    except ValueError :
                        print(f"Warning: unexpectd line \"{line}\"")
                else :
                    print(f"Warning: unexpected line \"{line}\"")

    def _update_lines_modified_by_author(self, author, stamp, inserted, deleted) :
        if author not in self.authors :
            self.authors[author] = {'lines_added' : 0, 'lines_removed' : 0, 'commits' : 0}
        self.authors[author]['commits'] = self.authors[author].get('commits', 0) + 1
        self.authors[author]['lines_added'] = self.authors[author].get('lines_added', 0) + inserted
        self.authors[author]['lines_removed'] = \
            self.authors[author].get('lines_removed', 0) + deleted
        if stamp not in self.changes_by_date_by_author :
            self.changes_by_date_by_author[stamp] = {}
        if author not in self.changes_by_date_by_author[stamp] :
            self.changes_by_date_by_author[stamp][author] = {}
        self.changes_by_date_by_author[stamp][author]['lines_added'] = \
            self.authors[author]['lines_added']
        self.changes_by_date_by_author[stamp][author]['commits'] = \
            self.authors[author]['commits']

    def _write_hour_of_day(self) :
        with open('hour_of_day.csv', 'w', encoding='utf-8') as outputfile :
            outputfile.write('Hour, Commits\n')
            for i in range(0, 24) :
                outputfile.write(f"{i}, {self.activity_by_hour_of_day.get(i, 0)}\n")

    def _write_day_of_week(self) :
        with open('day_of_week.csv', 'w', encoding='utf-8') as outputfile :
            outputfile.write('Weekday, Commits\n')
            for i, weekday in enumerate(calendar.day_abbr) :
                outputfile.write(f"{weekday}, {self.activity_by_day_of_week.get(i, 0)}\n")

    def _write_month_of_year(self) :
        with open('month_of_year.csv', 'w', encoding='utf-8') as outputfile :
            outputfile.write('Month, Commits\n')
            for i, _ in enumerate(calendar.month_name[1:], 1) :
                outputfile.write(f"{i}, {self.activity_by_month_of_year.get(i, 0)}\n")

    def _write_commits_by_year_month(self) :
        with open('commits_by_year_month.csv', 'w', encoding='utf-8') as outputfile :
            outputfile.write('Year-Month, Commits\n')
            for yymm in sorted(self.commits_by_month.keys()) :
                outputfile.write(f"{yymm}, {self.commits_by_month[yymm]}\n")

    def _write_commits_by_year(self) :
        with open('commits_by_year.csv', 'w', encoding='utf-8') as outputfile :
            outputfile.write('Year, Commits\n')
            for year in sorted(self.commits_by_year.keys()) :
                outputfile.write(f"{year}, {self.commits_by_year[year]}\n")


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

    git_statistics = GitStatisticsData(conf, gitpaths, outputpath)
    git_statistics.collect()
    git_statistics.write()

    time_end = time.time()
    exectime_total = time_end - time_start
    exectime_commands = git_statistics.get_exectime_commands()
    print(f"Execution time {exectime_total:.5f} secs, {exectime_commands:.5f} secs \
({(100.0*exectime_commands/exectime_total):.2f} %) in external commands")

if __name__ == '__main__' :
    main(sys.argv[1:])
