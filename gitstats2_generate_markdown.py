# -*- python-indent-offset: 4 -*-
import datetime
import time
from string import Template
import matplotlib
import pandas as pd

class RMarkdownFile :
    def __init__(self, templ, git_statistics) :
        self._template = Template(templ)
        self.git_statistics = git_statistics

    # def generate(self) :
    #     results = {
    #         'project_name' : '',
    #         'generation_date' : '',
    #         'generation_duration' : '',
    #         'commit_sha' : '',
    #         'git_version' : '',
    #         'pandas_version' : '',
    #         'matplotlib_version' : '',
    #         'start_date' : '',
    #         'end_date' : '',
    #         'total_days' : '',
    #         'active_days' : '',
    #         'perc_active_total' : '',
    #         'total_files' : '',
    #         'total_lines' : '',
    #         'added_lines' : '',
    #         'removed_lines' : '',
    #         'total_commits' : '',
    #         'avg_commits_per_active_day' : '',
    #         'avg_commits_per_day' : '',
    #         'authors' : '',
    #         'avg_commits_per_author' : '',
    #         'activity_period_weeks' : '',
    #         'weekly_activity_png' : '',
    #         'hour_of_day_table' : '',
    #         'hour_of_day_png' : '',
    #         'day_of_week_png' : '',
    #         'day_of_week_table' : '',
    #         'hour_of_week_png' : '',
    #         'month_of_year_png' : '',
    #         'month_of_year_table' : '',
    #         'commits_by_year_month_png' : '',
    #         'commits_by_year_month_table' : '',
    #         'commits_by_year_png' : '',
    #         'commits_by_year_table' : '',
    #         'commits_by_timezone_table' : '',
    #         'list_of_authors_table' : '',
    #         'lines_of_code_by_author_png' : '',
    #         'commits_by_author_png' : '',
    #         'author_of_month_table' : '',
    #         'author_of_year_table' : '',
    #         'domains_png' : '',
    #         'domains_table' : '',
    #         'file_size_bytes' : '',
    #         'files_by_date_png' : '',
    #         'file_extensions_table' : '',
    #         'lines_of_code_png' : '',
    #         'total_tags' : '',
    #         'avg_commits_per_tag' : '',
    #         'tags_table' : ''}
    #     results.update(self.git_statistics.configuration)
    #     # print(f"Current working directory {os.getcwd()}")
    #     out = self._template.substitute(results)
    #     return out

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
        perc_active_total = f"{(100.0*results['active_days']/results['total_days']):.2f}"
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
        results['authors'] = self.git_statistics.get_total_authors()
        avg_commits_per_author = \
            float(self.git_statistics.get_total_commits())/self.git_statistics.get_total_authors()
        results['avg_commits_per_author'] = f"{avg_commits_per_author:.1f}"

    def generate(self) :
        results = self.git_statistics.configuration.copy()
        self._fill_general(results)
        out = self._template.substitute(results)
        return out
