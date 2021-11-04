# -*- python-indent-offset: 4 -*-
import sys
import getopt
import os
import subprocess
import time
import datetime

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

    def get_runstart_stamp(self) :
        return self.runstart_stamp

    def get_gitstats2_version(self) :
        gitstats_repo = os.path.dirname(os.path.abspath(__file__))
        commit_range = '@'
        cmd = f"git --git-dir={gitstats_repo}/.git --work-tree={gitstats_repo} \
        rev-parse --short {commit_range}",
        return self._get_pipe_output([cmd])

    def get_git_version(self) :
        return self._get_pipe_output(['git --version'])

    def get_first_commit_date(self) :
        return datetime.datetime.fromtimestamp(self.first_commit_stamp)

    def get_last_commit_date(self) :
        return datetime.datetime.fromtimestamp(self.last_commit_stamp)

    def get_commit_delta_days(self) :
        return (self.last_commit_stamp / 86400 - self.first_commit_stamp / 86400) + 1

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
