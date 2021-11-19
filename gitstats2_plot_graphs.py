# -*- python-indent-offset: 4 -*-
import datetime
from dateutil import rrule
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
matplotlib.style.use('classic')

class GitStatisticsGraphs :
    def __init__(self, git_statistics) :
        self.git_statistics = git_statistics

    def plot_weekly_activity(self, activity_period_weeks) :
        activity_by_year_week = self.git_statistics.activity_by_year_week
        now = datetime.datetime.now()
        begin = now - datetime.timedelta(weeks=activity_period_weeks)
        weeks = tuple(rrule.rrule(rrule.WEEKLY, dtstart=begin, until=now))
        commits = map(lambda el : activity_by_year_week.get(el.strftime('%Y-%W'), 0), weeks)
        data = { 'Weeks' : weeks, 'Commits' : commits }
        plot_data = pd.DataFrame(data)
        plot_data.set_index('Weeks')
        plt.figure(figsize=(16.0, 6.0))
        plot_data['Commits'].plot(kind='bar', legend=None)
        locs, _labels = plt.xticks()
        plt.xticks(locs, map(lambda el : el.strftime('%Y-%W'), weeks), rotation=90)
        axes = plt.gca()
        axes.set_ylabel('Commits')
        plt.grid(True)
        plt.tight_layout()
        plt.savefig("weekly_activity.png")
        plt.close()

    @staticmethod
    def plot_hour_of_day() :
        plot_data = pd.read_csv('hour_of_day.csv', delimiter=', ', engine='python')
        plt.figure(figsize=(16.0, 6.0))
        plot_data['Commits'].plot(kind='bar', legend=None)
        plt.xticks(rotation=0)
        axes = plt.gca()
        axes.set_ylabel('Commits')
        plt.grid(True)
        plt.savefig("hour_of_day.png")
        plt.close()

    @staticmethod
    def plot_day_of_week() :
        plot_data = pd.read_csv('day_of_week.csv', delimiter=', ', engine='python')
        plt.figure(figsize=(16.0, 6.0))
        plot_data[['Weekday', 'Commits']].plot(kind='bar', legend=None)
        locs, _labels = plt.xticks()
        plt.xticks(locs, ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'), rotation=0)
        axes = plt.gca()
        axes.set_ylabel('Commits')
        plt.grid(True)
        plt.savefig("day_of_week.png")
        plt.close()

    @staticmethod
    def plot_month_of_year() :
        plot_data = pd.read_csv('month_of_year.csv', delimiter=', ', engine='python')
        plt.figure(figsize=(16.0, 6.0))
        plot_data['Commits'].plot(kind='bar', legend=None)
        locs, _labels = plt.xticks()
        plt.xticks(locs, plot_data.Month, rotation=0)
        axes = plt.gca()
        axes.set_ylabel('Commits')
        plt.grid(True)
        plt.savefig("month_of_year.png")
        plt.close()

    def plot_commits_by_year_month(self) :
        commits_by_month = self.git_statistics.get_commits_by_month()
        begin_yymm = min(commits_by_month.keys())
        begin_date = datetime.datetime.strptime(begin_yymm, '%Y-%m')
        begin_date -= datetime.timedelta(days=31)
        end_yymm = max(commits_by_month.keys())
        end_date = datetime.datetime.strptime(end_yymm, '%Y-%m')
        end_date += datetime.timedelta(days=31)
        year_months = tuple(rrule.rrule(rrule.MONTHLY, dtstart=begin_date, until=end_date))
        commits = map(lambda el : commits_by_month.get(el.strftime('%Y-%m'), 0), year_months)
        plot_data = { 'Year-Month' : year_months, 'Commits' : list(commits) }
        plt.figure(figsize=(16.0, 6.0))
        plt.fill_between(plot_data['Year-Month'], plot_data['Commits'], step='mid')
        axes = plt.gca()
        axes.set_ylabel('Commits')
        minor_locator = matplotlib.dates.DayLocator(bymonthday=[1])
        axes.xaxis.set_minor_locator(minor_locator)
        axes.tick_params(which='minor', length=5)
        axes.tick_params(which='major', length=7)
        plt.grid(True)
        plt.savefig("commits_by_year_month.png")
        plt.close()

    @staticmethod
    def plot_commits_by_year() :
        plot_data = pd.read_csv('commits_by_year.csv', delimiter=', ', engine='python')
        plt.figure(figsize=(16.0, 6.0))
        plot_data['Commits'].plot(kind='bar', legend=None)
        locs, _labels = plt.xticks()
        plt.xticks(locs, plot_data.Year, rotation=90)
        axes = plt.gca()
        axes.set_ylabel('Commits')
        plt.grid(True)
        plt.savefig("commits_by_year.png")
        plt.close()

    @staticmethod
    def plot_lines_of_code_by_author() :
        data = pd.read_csv('lines_of_code_by_author.csv', delimiter=', ', engine='python')
        plot_data = data.apply(lambda x : [datetime.datetime.fromtimestamp(elem) for elem in x]
                               if x.name == 'Stamp' else x)
        plt.figure(figsize=(16.0, 6.0))
        for author in plot_data.columns[1:] :
            plt.plot(plot_data.Stamp, plot_data[author], label=author)
        plt.legend(loc='upper left')
        axes = plt.gca()
        axes.set_ylabel('Lines')
        plt.grid(True)
        plt.savefig("lines_of_code_by_author.png")
        plt.close()

    @staticmethod
    def plot_commits_by_author() :
        data = pd.read_csv('commits_by_author.csv', delimiter=', ', engine='python')
        plot_data = data.apply(lambda x : [datetime.datetime.fromtimestamp(elem) for elem in x]
                               if x.name == 'Stamp' else x)
        plt.figure(figsize=(16.0, 6.0))
        for author in plot_data.columns[1:] :
            plt.plot(plot_data.Stamp, plot_data[author], label=author)
        plt.legend(loc='upper left')
        axes = plt.gca()
        axes.set_ylabel('Commits')
        plt.grid(True)
        plt.savefig("commits_by_author.png")
        plt.close()

    @staticmethod
    def plot_lines_of_code_added_by_author() :
        data = pd.read_csv('lines_of_code_added_by_author.csv', delimiter=', ', engine='python')
        plot_data = data.apply(lambda x : [datetime.datetime.fromtimestamp(elem) for elem in x]
                               if x.name == 'Stamp' else x)
        plt.figure(figsize=(16.0, 6.0))
        for author in plot_data.columns[1:] :
            plt.plot(plot_data.Stamp, plot_data[author], label=author)
        plt.legend(loc='upper left')
        axes = plt.gca()
        axes.set_ylabel('Lines')
        plt.grid(True)
        plt.savefig("lines_of_code_added_by_author.png")
        plt.close()

    @staticmethod
    def plot_domains() :
        plot_data = pd.read_csv('domains.csv', delimiter=', ', engine='python')
        plot_data.set_index('Ranking')
        plt.figure(figsize=(16.0, 6.0))
        # pylint: disable=unsubscriptable-object
        plot_data['Commits'].plot(kind='bar', legend=None)
        locs, _labels = plt.xticks()
        # pylint: disable=E1101
        plt.xticks(locs, plot_data.Domain, rotation=0)
        axes = plt.gca()
        axes.set_ylabel('Commits')
        plt.grid(True)
        plt.savefig("domains.png")
        plt.close()

    @staticmethod
    def plot_files_by_date() :
        data = pd.read_csv('files_by_date.csv', delimiter=', ', engine='python')
        plot_data = data.apply(lambda x : [datetime.datetime.fromtimestamp(elem) for elem in x]
                               if x.name == 'Timestamp' else x)
        plt.figure(figsize=(16.0, 6.0))
        plt.plot(plot_data.Timestamp, plot_data['Total files'])
        axes = plt.gca()
        axes.set_ylabel('Files')
        plt.grid(True)
        plt.savefig("files_by_date.png")
        plt.close()

    @staticmethod
    def plot_lines_of_code() :
        data = pd.read_csv('lines_of_code.csv', delimiter=', ', engine='python')
        plot_data = data.apply(lambda x : [datetime.datetime.fromtimestamp(elem) for elem in x]
                               if x.name == 'Timestamp' else x)
        plt.figure(figsize=(16.0, 6.0))
        plt.plot(plot_data.Timestamp, plot_data['Total Lines'])
        axes = plt.gca()
        axes.set_ylabel('Lines')
        plt.grid(True)
        plt.tight_layout()
        plt.savefig("lines_of_code.png")
        plt.close()
