# Author: George K. Holt
# Date: 2021-02-22
# License: MIT
"""deadline_bot.py

Usage:
> python deadline_bot.py --bot-token <bot_token> --chat-id <chat_id> --deadline-str <yyyy-mm-dd> --goal-pages <int>
"""
import matplotlib
matplotlib.use('Agg')
import os
import requests
import argparse
import datetime
import time
import pandas as pd
import matplotlib.pyplot as plt

class Deadline():
    '''Target deadline and progress.'''
    def __init__(self, deadline_str, goal_pages):
        self.deadline_str = deadline_str
        self.deadline = pd.to_datetime(self.deadline_str)
        self.goal_pages = goal_pages
        self.df = pd.read_csv('date-page.csv')
        self.start_date = pd.to_datetime(self.df.iloc[0]['Date'])
        self.current_pages = self.df.iloc[-1]['Pages']
    
    def calc_deadline(self):
        '''Calculate requirements to meet deadline.''' 
        days_left = (self.deadline - datetime.datetime.today()).days
        weekdays_left = 0
        curr_day = datetime.datetime.today()
        while curr_day.date() != self.deadline.date():
            if curr_day.weekday() < 6:
                weekdays_left += 1
            curr_day += datetime.timedelta(days=1)
        pages_left = self.goal_pages - self.current_pages
        avg_pages_per_day_left = pages_left / days_left
        avg_pages_per_weekday_left = pages_left / weekdays_left
        return days_left, weekdays_left, pages_left, avg_pages_per_day_left, avg_pages_per_weekday_left
    
    def calc_progress(self):
        '''Calculate progress towards goal.'''
        current_date = pd.Timestamp.today()
        days_gone = current_date - self.start_date
        if days_gone.days > 0:
            avg_pages_per_day = self.current_pages / days_gone.days
        else:
            avg_pages_per_day = None
        return current_date, days_gone.days, avg_pages_per_day
    
    def construct_message(self):
        '''Construct a message to summarise deadline progress.'''
        days_left, weekdays_left, pages_left, avg_pages_per_day_left, avg_pages_per_weekday_left = self.calc_deadline()
        current_date, days_gone, avg_pages_per_day = self.calc_progress()
        
        msg = f"Progress update for {current_date.strftime('%Y-%m-%d')}\n\n"
       
        msg += f"Current pages: {self.current_pages}\n"
        msg += f"Pages left: {pages_left}\n"
        msg += f"Days left: {days_left}\n"
        msg += f"Weekdays left: {weekdays_left}\n"
        msg += f"Avg pages per day to meet goal ({self.goal_pages}) by "\
               f"deadline ({self.deadline.strftime('%Y-%m-%d')}): "\
               f"{avg_pages_per_day_left:.2f}\n"
        msg += f"Avg pages per weekday: {avg_pages_per_weekday_left:.2f}\n\n"
        
        msg += f"Days since started writing: {days_gone}\n"
        if avg_pages_per_day is not None:
            msg += f"Avg pages per day so far: {avg_pages_per_day:.2f}\n"
        
        return msg
    
    def create_image(self):
        fig, ax = plt.subplots()
        ax.plot(
            [self.start_date, self.deadline],
            [self.df.iloc[0]['Pages'], self.goal_pages],
            label="From start",
            ls='--',
            c='C0'
        )
        ax.plot(
            [pd.Timestamp.today().date(), self.deadline],
            [self.current_pages, self.goal_pages],
            label="From today",
            ls=':',
            c='C1'
        )
        ax.plot(
            pd.to_datetime(self.df['Date']),
            self.df['Pages'],
            label="Data",
            ls='-',
            c='C2'
        )
        ax.set_xlabel('Date')
        ax.set_ylabel('Pages')
        ax.tick_params(axis='x', rotation=45)
        ax.legend()
        ax.grid()
        fig.tight_layout()
        fig.canvas.draw()
        ax.set_ylim(0, ax.get_ylim()[1])
        fig.tight_layout()
        tmp_file = 'temp_image.png'
        fig.savefig(tmp_file, format='png')
        return tmp_file
    
    def clean_up(self, tmp_file):
        os.remove(tmp_file)
             
def construct_text_url(token, chat_id, msg):
    '''Create URL to send msg via Telegram API.'''
    url = 'https://api.telegram.org/bot'
    url += token
    url += '/sendMessage?chat_id='
    url += chat_id
    url += '&text='
    url += msg
    return url

def send_img(token, chat_id, img_file):
    '''Send image via Telegram API.'''
    url = 'https://api.telegram.org/bot'
    url += token
    url += '/sendPhoto'
    file = {'photo': open(img_file, 'rb')}
    requests.get(url, params={'chat_id': chat_id}, files=file)
    
def sleep_one_day():
    '''Sleep until 07:00 next day.'''
    now = datetime.datetime.now()
    tomorrow = now.date() + datetime.timedelta(days=1)
    target = datetime.datetime.combine(tomorrow, datetime.time(hour=7))
    sleep_time = target - now
    time.sleep(sleep_time.total_seconds())
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--bot-token', type=str, required=True)
    parser.add_argument('--chat-id', type=str, required=True)
    parser.add_argument('--deadline-str', type=str, required=True)
    parser.add_argument('--goal-pages', type=int, required=True)
    args = parser.parse_args()
     
    while True:
        deadline = Deadline(args.deadline_str, args.goal_pages)

        # Text report
        url = construct_text_url(
            args.bot_token, args.chat_id, deadline.construct_message()
        )
        requests.get(url)
        
        # Graph
        tmp_file = deadline.create_image()
        send_img(args.bot_token, args.chat_id, tmp_file)
        deadline.clean_up(tmp_file)
        
        sleep_one_day()
