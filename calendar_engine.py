import requests
import json
from datetime import datetime, timedelta
import dateutil.parser
import pytz

class EconomicCalendar:
    def __init__(self):
        self.url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        self.events = []
        self.last_update = None

    def fetch_events(self):
        """Fetches and parses the latest economic events"""
        try:
            res = requests.get(self.url, timeout=10)
            if res.status_code == 200:
                self.events = res.json()
                self.last_update = datetime.now()
                return True
        except Exception as e:
            print(f"Calendar Fetch Error: {e}")
        return False

    def get_upcoming_high_impact(self, hours=24):
        """Returns a list of High Impact events in the next X hours"""
        if not self.events:
            self.fetch_events()
            
        now = datetime.now(pytz.utc)
        upcoming = []
        
        for event in self.events:
            if event.get('impact') == 'High':
                try:
                    event_time = dateutil.parser.isoparse(event['date'])
                    time_diff = (event_time - now).total_seconds() / 3600.0
                    
                    if 0 <= time_diff <= hours:
                        event['time_until'] = round(time_diff * 60, 0) # in minutes
                        upcoming.append(event)
                except:
                    continue
        
        return upcoming

    def is_news_active(self, buffer_before=15, buffer_after=15):
        """Checks if we are currently in a high-impact news window"""
        if not self.events:
            self.fetch_events()

        now = datetime.now(pytz.utc)
        for event in self.events:
            if event.get('impact') == 'High':
                try:
                    event_time = dateutil.parser.isoparse(event['date'])
                    start_pause = event_time - timedelta(minutes=buffer_before)
                    end_pause = event_time + timedelta(minutes=buffer_after)
                    
                    if start_pause <= now <= end_pause:
                        return True, event['title']
                except:
                    continue
        return False, None

if __name__ == "__main__":
    cal = EconomicCalendar()
    if cal.fetch_events():
        print(f"Successfully fetched {len(cal.events)} events.")
        high = cal.get_upcoming_high_impact(48)
        print("\n--- HIGH IMPACT EVENTS (Next 48h) ---")
        for e in high:
            print(f"- {e['title']} ({e['country']}) in {e['time_until']} mins")
