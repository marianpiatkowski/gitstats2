# -*- python-indent-offset: 4 -*-
import sys
import getopt
import os
import subprocess
import gitstats2_markdown
from gitstats2_collect_data import GitStatisticsData
from gitstats2_generate_markdown import RMarkdownFile

def main(args_orig) :
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

    git_statistics = GitStatisticsData(conf, gitpaths, outputpath)
    git_statistics.collect()
    file_generator = RMarkdownFile(gitstats2_markdown.template, git_statistics)
    os.chdir(outputpath)
    with open(gitstats2_markdown.filename, 'w') as fout:
        fout.write(file_generator.generate())
    subprocess.run(
        f"Rscript -e \"rmarkdown::render('{gitstats2_markdown.filename}')\"",
        shell=True,
        check=True)

if __name__ == '__main__' :
    main(sys.argv[1:])
