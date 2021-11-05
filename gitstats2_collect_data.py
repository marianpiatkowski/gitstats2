# -*- python-indent-offset: 4 -*-
import sys
import getopt
import os
import subprocess
import time
import datetime
import re

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

    def collect(self) :
        self.runstart_stamp = time.time()
        self.exectime_commands = 0.0
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

    time_end = time.time()
    exectime_total = time_end - time_start
    exectime_commands = git_statistics.get_exectime_commands()
    print(f"Execution time {exectime_total:.5f} secs, {exectime_commands:.5f} secs \
({(100.0*exectime_commands/exectime_total):.2f} %) in external commands")

if __name__ == '__main__' :
    main(sys.argv[1:])
