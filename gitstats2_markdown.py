# -*- python-indent-offset: 4 -*-
filename = 'index.Rmd'

template = '''\
---
title: GitStats2 - $project_name
output: html_document
---

## {.tabset}

### General

#### Project name:

$project_name

#### Generated:

$generation_date (in $generation_duration seconds)

#### Generator:

[GitStats2](https://github.com/marianpiatkowski/gitstats2) (version $commit_sha), $git_version, pandas version $pandas_version, matplotlib version $matplotlib_version, R version `r getRversion()`

#### Report Period:

$start_date to $end_date

#### Age:

$total_days days, $active_days active days ($perc_active_total %)

#### Total files:

$total_files

#### Total lines of code:

$total_lines ($added_lines added, $removed_lines removed)

#### Total commits:

$total_commits (average $avg_commits_per_active_day per active day, $avg_commits_per_day per all days)

#### Authors:

$authors (average $avg_commits_per_author commits per author)

### Activity

~~~
Weekly activity
~~~
Last $activity_period_weeks weeks
$weekly_activity_png

~~~
Hour of day
~~~
$hour_of_day_table
$hour_of_day_png

~~~
Day of week
~~~
$day_of_week_png
$day_of_week_table

~~~
Hour of week
~~~
$hour_of_week_table

~~~
Month of year
~~~
$month_of_year_png
$month_of_year_table

~~~
Commits by year/month
~~~
$commits_by_year_month_png
$commits_by_year_month_table

~~~
Commits by year
~~~
$commits_by_year_png
$commits_by_year_table

~~~
Commits by timezone
~~~
$commits_by_timezone_table

### Authors

~~~
List of Authors
~~~
$list_of_authors_table

~~~
Cumulated added lines of code per author
~~~
$lines_of_code_by_author_png

~~~
Commits per author
~~~
$commits_by_author_png

~~~
Author of month
~~~
$author_of_month_table

~~~
Author of year
~~~
$author_of_year_table

~~~
Commits by domains
~~~
$domains_png
$domains_table

### Files

#### Total files:

$total_files

#### Total lines:

$total_lines

#### Average file size:

$file_size_bytes bytes

~~~
File count by date
~~~
$files_by_date_png

~~~
Extensions
~~~
$file_extensions_table

### Lines

#### Total lines:

$total_lines

~~~
Lines of code
~~~
$lines_of_code_png
$lines_of_code_by_author_png

### Tags

#### Total tags:

$total_tags

#### Average commits per tag:

$avg_commits_per_tag

$tags_table
'''
