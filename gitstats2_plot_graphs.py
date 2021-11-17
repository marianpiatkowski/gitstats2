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
        weeks = []
        commits = []
        now = datetime.datetime.now()
        begin = now - datetime.timedelta(weeks=activity_period_weeks)
        for date in rrule.rrule(rrule.WEEKLY, dtstart=begin, until=now) :
            weeks.append(date)
            yyw = date.strftime('%Y-%W')
            commits.append(self.git_statistics.activity_by_year_week.get(yyw, 0))
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
        plt.tight_layout()
        plt.savefig("lines_of_code_by_author.png")
        plt.close()
