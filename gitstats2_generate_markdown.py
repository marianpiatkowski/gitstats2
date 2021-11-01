# -*- python-indent-offset: 4 -*-
import os
from string import Template
import gitstats2_markdown

class RMarkdownFile :
    def __init__(self, templ, git_statistics) :
        self._template = Template(templ)
        self._git_statistics = git_statistics

    def generate(self) :
        results = {
            'project_name' : '',
            'generation_date' : '',
            'generation_duration' : '',
            'commit_sha' : '',
            'git_version' : '',
            'pandas_version' : '',
            'matplotlib_version' : '',
            'R_version' : '',
            'start_date' : '',
            'end_date' : '',
            'total_days' : '',
            'active_days' : '',
            'perc_active_total' : '',
            'total_files' : '',
            'total_lines' : '',
            'added_lines' : '',
            'removed_lines' : '',
            'total_commits' : '',
            'avg_commits_per_active_day' : '',
            'avg_commits_per_day' : '',
            'authors' : '',
            'avg_commits_per_author' : '',
            'activity_period_weeks' : '',
            'weekly_activity_png' : '',
            'hour_of_day_table' : '',
            'hour_of_day_png' : '',
            'day_of_week_png' : '',
            'day_of_week_table' : '',
            'hour_of_week_png' : '',
            'month_of_year_png' : '',
            'month_of_year_table' : '',
            'commits_by_year_month_png' : '',
            'commits_by_year_month_table' : '',
            'commits_by_year_png' : '',
            'commits_by_year_table' : '',
            'commits_by_timezone_table' : '',
            'list_of_authors_table' : '',
            'lines_of_code_by_author_png' : '',
            'commits_by_author_png' : '',
            'author_of_month_table' : '',
            'author_of_year_table' : '',
            'domains_png' : '',
            'domains_table' : '',
            'file_size_bytes' : '',
            'files_by_date_png' : '',
            'file_extensions_table' : '',
            'lines_of_code_png' : '',
            'total_tags' : '',
            'avg_commits_per_tag' : '',
            'tags_table' : ''}
        results.update(self._git_statistics.configuration)
        # print(f"Current working directory {os.getcwd()}")
        out = self._template.substitute(results)
        return out
