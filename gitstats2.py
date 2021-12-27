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
import time
import getopt
import os
import pickle
import subprocess
import gitstats2_collect_data

if sys.version_info < (3, 6) :
    print("Python 3.6 or higher is required for gitstats2", file=sys.stderr)
    sys.exit(1)

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
Usage: gitstats2.py [options] <gitpath..> <outputpath>

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

    git_statistics = gitstats2_collect_data.GitStatisticsData(conf, gitpaths)
    git_statistics.collect()
    statistics_writer = gitstats2_collect_data.GitStatisticsWriter(git_statistics)
    statistics_writer.write(outputpath)
    prev_dir = os.getcwd()
    os.chdir(outputpath)
    with open('git_statistics.pkl', 'wb') as fout :
        pickle.dump(git_statistics, fout, pickle.HIGHEST_PROTOCOL)
    os.chdir(prev_dir)

    subprocess.call(f"python3 gitstats2_generate_markdown.py {outputpath}", shell=True)

    time_end = time.time()
    exectime_total = time_end - time_start
    exectime_commands = gitstats2_collect_data.get_pipe_output.exectime_commands
    print(f"Execution time {exectime_total:.5f} secs, {exectime_commands:.5f} secs \
({(100.0*exectime_commands/exectime_total):.2f} %) in external commands")

if __name__ == '__main__' :
    main(sys.argv[1:])
