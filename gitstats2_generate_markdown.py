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
import os
import pickle
import subprocess
import datetime
import time
import calendar
from string import Template
import pandas as pd
import matplotlib
import gitstats2_markdown
from gitstats2_plot_graphs import GitStatisticsGraphs
from gitstats2_collect_data import GitStatisticsData # pylint: disable=W0611

if sys.version_info < (3, 6) :
    print("Python 3.6 or higher is required for gitstats2", file=sys.stderr)
    sys.exit(1)

class RMarkdownFile :
    def __init__(self, templ, git_statistics) :
        self._template = Template(templ)
        self.git_statistics = git_statistics
        self.statistics_viewer = GitStatisticsGraphs(git_statistics)

    def generate(self) :
        results = self.git_statistics.configuration.copy()
        self._fill_general(results)
        self._fill_activity(results)
        self._fill_authors(results)
        self._fill_files(results)
        self._fill_lines(results)
        self._fill_tags(results)
        out = self._template.substitute(results)
        return out

    def _fill_general(self, results) :
        datetime_format = '%Y-%m-%d %H:%M:%S'
        results['generation_date'] = datetime.datetime.now().strftime(datetime_format)
        results['generation_duration'] = \
            f"{(time.time() - self.git_statistics.get_runstart_stamp()):.1f}"
        results['commit_sha'] = self.git_statistics.get_gitstats2_version()
        results['git_version'] = self.git_statistics.get_git_version()
        results['pandas_version'] = pd.__version__
        results['matplotlib_version'] = matplotlib.__version__
        results['start_date'] = \
            self.git_statistics.get_first_commit_date().strftime(datetime_format)
        results['end_date'] = \
            self.git_statistics.get_last_commit_date().strftime(datetime_format)
        results['total_days'] = self.git_statistics.get_commit_delta_days()
        results['active_days'] = len(self.git_statistics.get_active_days())
        perc_active_total = f"{(results['active_days']/results['total_days']):.2%}"
        results['perc_active_total'] = perc_active_total
        results['total_files'] = self.git_statistics.get_total_files()
        results['total_lines'] = self.git_statistics.get_total_lines_of_code()
        results['added_lines'] = self.git_statistics.get_total_lines_added()
        results['removed_lines'] = self.git_statistics.get_total_lines_removed()
        results['total_commits'] = self.git_statistics.get_total_commits()
        avg_commits_per_active_day = \
            float(self.git_statistics.get_total_commits())/len(self.git_statistics.get_active_days())
        results['avg_commits_per_active_day'] = f"{avg_commits_per_active_day:.1f}"
        avg_commits_per_day = \
            float(self.git_statistics.get_total_commits())/self.git_statistics.get_commit_delta_days()
        results['avg_commits_per_day'] = f"{avg_commits_per_day:.1f}"
        total_authors = len(self.git_statistics.get_total_authors())
        results['authors'] = total_authors
        avg_commits_per_author = \
            float(self.git_statistics.get_total_commits())/total_authors
        results['avg_commits_per_author'] = f"{avg_commits_per_author:.1f}"

    def _fill_activity(self, results) :
        activity_period_weeks = 32
        results['activity_period_weeks'] = activity_period_weeks
        self.statistics_viewer.plot_weekly_activity(activity_period_weeks)
        results['weekly_activity_png'] = '![WeeklyActivity](weekly_activity.png)'
        self._fill_hour_of_day_table(results)
        self.statistics_viewer.plot_hour_of_day()
        results['hour_of_day_png'] = '![HourOfDay](hour_of_day.png)'
        self.statistics_viewer.plot_day_of_week()
        results['day_of_week_png'] = '![DayOfWeek](day_of_week.png)'
        self._fill_day_of_week_table(results)
        self._fill_hour_of_week_table(results)
        self.statistics_viewer.plot_month_of_year()
        results['month_of_year_png'] = '![MonthOfYear](month_of_year.png)'
        self._fill_month_of_year_table(results)
        self.statistics_viewer.plot_commits_by_year_month()
        results['commits_by_year_month_png'] = '![CommitsByYearMonth](commits_by_year_month.png)'
        self._fill_commits_by_year_month_table(results)
        self.statistics_viewer.plot_commits_by_year()
        results['commits_by_year_png'] = '![CommitsByYear](commits_by_year.png)'
        self._fill_commits_by_year_table(results)
        self._fill_commits_by_timezone_table(results)

    def _fill_hour_of_day_table(self, results) :
        activity_by_hour_of_day = self.git_statistics.get_activity_by_hour_of_day()
        total_commits = sum(activity_by_hour_of_day.values())
        hour_of_day_table = []
        for i in range(0, 24) :
            commits = activity_by_hour_of_day.get(i, 0)
            hour_of_day_table.append([commits, f"{(commits/total_commits):.2%}"])
        _df = pd.DataFrame(hour_of_day_table, columns=['Commits', 'Percentage'])
        df_transposed = _df.transpose()
        results['hour_of_day_table'] = \
            df_transposed.to_markdown(tablefmt="github", numalign="center")

    @staticmethod
    def _fill_day_of_week_table(results) :
        data = pd.read_csv('day_of_week.csv', delimiter=', ', engine='python', index_col='Weekday')
        total_commits = sum(data.Commits)
        # pylint: disable=E1136 disable=E1137
        data['Commits'] = \
            data['Commits'].map(lambda el : f"{el} ({(el/total_commits):.2%})")
        # pylint: disable=E1101
        data_transposed = data.transpose()
        results['day_of_week_table'] = \
            data_transposed.to_markdown(tablefmt="github", numalign="center")

    def _fill_hour_of_week_table(self, results) :
        activity_by_hour_of_week = self.git_statistics.get_activity_by_hour_of_week()
        table = []
        for weekday in calendar.Calendar().iterweekdays() :
            if weekday in activity_by_hour_of_week :
                table.append(
                    [ activity_by_hour_of_week[weekday].get(hour, 0) for hour in range(0, 24)])
            else :
                table.append([0]*24)
        data = pd.DataFrame(table, index=calendar.day_abbr, columns=range(0, 24))
        results['hour_of_week_table'] = data.to_markdown(tablefmt="github", numalign="center")

    @staticmethod
    def _fill_month_of_year_table(results) :
        data = pd.read_csv('month_of_year.csv', delimiter=', ', engine='python', index_col='Month')
        total_commits = sum(data.Commits)
        # pylint: disable=E1136 disable=E1137
        data['Commits'] = data['Commits'].map(lambda el : f"{el} ({(el/total_commits):.2%})")
        # pylint: disable=E1101
        data_transposed = data.transpose()
        results['month_of_year_table'] = \
            data_transposed.to_markdown(tablefmt="github", numalign="center")

    def _fill_commits_by_year_month_table(self, results) :
        commits_by_month = self.git_statistics.get_commits_by_month()
        lines_added_by_month = self.git_statistics.get_lines_added_by_month()
        lines_removed_by_month = self.git_statistics.get_lines_removed_by_month()
        table = []
        for yymm in sorted(commits_by_month.keys(), reverse=True) :
            row = [yymm, commits_by_month[yymm],
                   lines_added_by_month.get(yymm, 0), lines_removed_by_month.get(yymm, 0)]
            table.append(row)
        data = pd.DataFrame(table, columns=['Month', 'Commits', 'Lines added', 'Lines removed'])
        results['commits_by_year_month_table'] = \
            data.to_markdown(index=False, tablefmt="github", numalign="center")

    def _fill_commits_by_year_table(self, results) :
        commits_by_year = self.git_statistics.get_commits_by_year()
        lines_added_by_year = self.git_statistics.get_lines_added_by_year()
        lines_removed_by_year = self.git_statistics.get_lines_removed_by_year()
        total_commits = sum(commits_by_year.values())
        table = []
        for year in sorted(commits_by_year.keys(), reverse=True) :
            commits = commits_by_year[year]
            row = [year, f"{commits} ({(commits/total_commits):.2%})",
                   lines_added_by_year.get(year, 0), lines_removed_by_year.get(year, 0)]
            table.append(row)
        data = pd.DataFrame(
            table,
            columns=['Year', 'Commits (% of all)', 'Lines added', 'Lines removed'])
        results['commits_by_year_table'] = \
            data.to_markdown(index=False, tablefmt="github", numalign="center")

    def _fill_commits_by_timezone_table(self, results) :
        commits_by_timezone = self.git_statistics.get_commits_by_timezone()
        table = [ [timezone, commits_by_timezone[timezone]]
                  for timezone in sorted(commits_by_timezone.keys())]
        data = pd.DataFrame(table, columns=['Timezone', 'Commits'])
        results['commits_by_timezone_table'] = \
            data.to_markdown(index=False, tablefmt="github", numalign="center")

    def _fill_authors(self, results) :
        self._fill_authors_table(results)
        self.statistics_viewer.plot_commits_by_author()
        results['commits_by_author_png'] = '![CommitsByAuthor](commits_by_author.png)'
        self.statistics_viewer.plot_lines_of_code_added_by_author()
        results['lines_of_code_added_by_author_png'] = \
            '![LinesOfCodeAddedByAuthor](lines_of_code_added_by_author.png)'
        self._fill_author_of_month_table(results)
        self._fill_author_of_year_table(results)
        self.statistics_viewer.plot_domains()
        results['domains_png'] = '![Domains](domains.png)'
        self._fill_domains_table(results)

    def _fill_authors_table(self, results) :
        limit = self.git_statistics.configuration['max_authors']
        authors = self.git_statistics.authors
        authors_to_write = self.git_statistics.get_authors(limit)
        total_commits = self.git_statistics.get_total_commits()
        table = []
        for i, author in enumerate(authors_to_write, 1) :
            author_stats = authors[author]
            commits = author_stats['commits']
            lines_added = author_stats['lines_added']
            lines_removed = author_stats['lines_removed']
            first_commit = datetime.datetime.fromtimestamp(author_stats['first_commit_stamp'])
            last_commit = datetime.datetime.fromtimestamp(author_stats['last_commit_stamp'])
            timedelta = last_commit - first_commit
            active_days = len(author_stats['active_days'])
            ranking = i
            row = [author, f"{commits} ({(commits/total_commits):.2%})",
                   lines_added, lines_removed,
                   first_commit.strftime("%Y-%m-%d"), last_commit.strftime("%Y-%m-%d"),
                   timedelta, active_days, ranking]
            table.append(row)
        # pylint: disable=C0301
        data = pd.DataFrame(
            table,
            columns=['Author', 'Commits (%)', '+ lines', '- lines', 'First Commit', 'Last commit', 'Age', 'Active days', '# by commits'])
        results['list_of_authors_table'] = \
            data.to_markdown(index=False, tablefmt="github", numalign="center")

        rest_authors = set(authors.keys()).difference(authors_to_write)
        if rest_authors :
            results['more_authors_list'] = \
                f"These didn't make it to the top: {', '.join(rest_authors)}"
        else :
            results['more_authors_list'] = ''

    def _fill_author_of_month_table(self, results) :
        author_of_month = self.git_statistics.get_author_of_month()
        limit = self.git_statistics.configuration['authors_top']
        table = []
        for yymm in sorted(author_of_month.keys(), reverse=True) :
            authors = author_of_month[yymm]
            commits_by_month = sum(authors.values())
            authors_by_commits = sorted(authors, key=authors.get, reverse=True)
            most_commits = authors[authors_by_commits[0]]
            authors_top_rest = ', '.join(authors_by_commits[1:limit+1])
            # pylint: disable=C0301
            row = [
                yymm, authors_by_commits[0],
                f"{most_commits} ({(most_commits/commits_by_month):.2%} of {commits_by_month})",
                authors_top_rest, len(authors)]
            table.append(row)
        data = pd.DataFrame(
            table,
            columns=['Month', 'Author', 'Commits (%)', f"Next top {limit}", "Number of authors"])
        results['author_of_month_table'] = \
            data.to_markdown(index=False, tablefmt="github", numalign="center")

    def _fill_author_of_year_table(self, results) :
        author_of_year = self.git_statistics.get_author_of_year()
        limit = self.git_statistics.configuration['authors_top']
        table = []
        for year in sorted(author_of_year.keys(), reverse=True) :
            authors = author_of_year[year]
            commits_by_year = sum(authors.values())
            authors_by_commits = sorted(authors, key=authors.get, reverse=True)
            most_commits = authors[authors_by_commits[0]]
            authors_top_rest = ', '.join(authors_by_commits[1:limit+1])
            # pylint: disable=C0301
            row = [
                year, authors_by_commits[0],
                f"{most_commits} ({(most_commits/commits_by_year):.2%} of {commits_by_year})",
                authors_top_rest, len(authors)]
            table.append(row)
        data = pd.DataFrame(
            table,
            columns=['Month', 'Author', 'Commits (%)', f"Next top {limit}", "Number of authors"])
        results['author_of_year_table'] = \
            data.to_markdown(index=False, tablefmt="github", numalign="center")

    def _fill_domains_table(self, results) :
        domains = self.git_statistics.get_domains_sorted_by_commits(reverse=True)
        total_commits = self.git_statistics.get_total_commits()
        table = [ [domain, f"{info['commits']} ({(info['commits']/total_commits):.2%})"]
                  for domain, info in domains]
        data = pd.DataFrame(table, columns=['Domains', 'Total (%)'])
        results['domains_table'] = \
            data.to_markdown(index=False, tablefmt="github", numalign="center")

    def _fill_files(self, results) :
        total_size = self.git_statistics.get_total_size()
        total_files = self.git_statistics.get_total_files()
        avg_file_size_bytes = f"{(total_size/total_files):.2f}"
        results['file_size_bytes'] = avg_file_size_bytes
        self.statistics_viewer.plot_files_by_date()
        results['files_by_date_png'] = '![FilesByDate](files_by_date.png)'
        self._fill_file_extensions_table(results)

    def _fill_file_extensions_table(self, results) :
        extensions = self.git_statistics.get_extensions()
        total_files = self.git_statistics.get_total_files()
        total_lines = self.git_statistics.get_total_lines_of_code()
        table = []
        for extension in sorted(extensions.keys()) :
            files = extensions[extension]['files']
            lines = extensions[extension]['lines']
            row = [
                extension,
                f"{files} ({(files/total_files):.2%})",
                f"{lines} ({(lines/total_lines):.2%})",
                lines // files]
            table.append(row)
        data = pd.DataFrame(table, columns=['Extension', 'Files (%)', 'Lines (%)', 'Lines/file'])
        results['file_extensions_table'] = \
            data.to_markdown(index=False, tablefmt="github", numalign="center")

    def _fill_lines(self, results) :
        self.statistics_viewer.plot_lines_of_code()
        results['lines_of_code_png'] = '![LinesOfCode](lines_of_code.png)'
        if self.git_statistics.configuration['lines_by_date'] :
            self.statistics_viewer.plot_lines_of_code_by_author()
            results['lines_of_code_by_author_png'] = \
                '![LinesOfCodeByAuthor](lines_of_code_by_author.png)'
        else :
            results['lines_of_code_by_author_png'] = ''

    def _fill_tags(self, results) :
        tags = self.git_statistics.tags
        total_tags = 0
        tags_table = []
        for repository in tags.keys() :
            if not tags[repository] :
                continue
            total_tags += len(tags[repository])
            tags_table.extend(self._fill_tags_table(repository, tags))

        results['total_tags'] = total_tags
        avg_commits_per_tag = float(0.0)
        if total_tags :
            avg_commits_per_tag = self.git_statistics.get_total_commits()/total_tags
        results['avg_commits_per_tag'] = f"{avg_commits_per_tag:.2f}"

        if not tags_table :
            results['tags_table'] = ''
            return
        _df = pd.DataFrame(tags_table, columns=["Repository", "Name", "Date", "Commits", "Authors"])
        results['tags_table'] = _df.to_markdown(index=False, tablefmt="github", numalign="center")

    @staticmethod
    def _fill_tags_table(repository, tags) :
        tags_table = []
        for tagname, tagdetails in tags[repository].items() :
            tags_row = [repository, tagname]
            tags_row.append(tagdetails['date'])
            tags_row.append(tagdetails['commits'])
            authors_w_commits = []
            for author, commits in tagdetails['authors'].items() :
                authors_w_commits.append(f"{author} ({commits})")
            tags_row.append(', '.join(authors_w_commits))
            tags_table.append(tags_row)
        return tags_table

def main(args) :
    def usage() :
        print('Usage: gitstats2_generate_markdown.py <path>')
    if len(args) != 1 :
        usage()
        sys.exit(0)
    path = args[0]
    prev_dir = os.getcwd()
    os.chdir(path)
    with open('git_statistics.pkl', 'rb') as inp :
        git_statistics = pickle.load(inp)
        file_generator = RMarkdownFile(gitstats2_markdown.template, git_statistics)
    with open(gitstats2_markdown.filename, 'w') as fout:
        fout.write(file_generator.generate())
    subprocess.run(
        f"Rscript -e \"rmarkdown::render('{gitstats2_markdown.filename}')\"",
        shell=True,
        check=True)
    os.chdir(prev_dir)

if __name__ == '__main__' :
    main(sys.argv[1:])
