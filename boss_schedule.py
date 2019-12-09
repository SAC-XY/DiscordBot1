import logging
import sys
import traceback
from datetime import datetime, timezone, timedelta
from apiclient import discovery
from google.oauth2 import service_account
from httplib2 import Http

logger = logging.getLogger(__name__)

class GoogleCalendar(object):
    def __init__(self, calendar_id):
        self.calendar_id = calendar_id
        pass

    def get_credentials(self):
        client_secret_file = 'client_secret.json'
        scope = [
            'https://www.googleapis.com/auth/calendar'
        ]
        credentials = service_account.Credentials.from_service_account_file(client_secret_file, scopes=scope)
        return credentials

    def get_schedule(self, calendar_id, time_min, time_max):
        try:
            credentials = self.get_credentials()

            service = discovery.build('calendar', 'v3',
                                      credentials=credentials,
                                      cache_discovery=False)

            events = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                maxResults=20
            ).execute()
            items = events['items']

            return items

        except Exception as e:
            logger.error(traceback.format_exc(sys.exc_info()[2]))

    def one_week_boss_schedule_messages(self):
        now = datetime.now(timezone.utc).astimezone()

        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = week_start.isoformat('T')

        week_end = now + timedelta(days=(7 - now.weekday()))
        week_end = week_end.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_end.isoformat('T')

        schedules = self.get_schedule(
            self.calendar_id,
            week_start,
            week_end
        )
        before_sort = [(x["summary"], datetime.fromisoformat(x['start']['dateTime']).weekday(), x['start']['dateTime']) for x in schedules]
        sorted_schedules = sorted(before_sort, key=lambda x: datetime.fromisoformat(x[2]))

        weekday = ('月', '火', '水', '木', '金', '土', '日')
        return [v + ' : ' + ' / '.join([x[0] for x in sorted_schedules if x[1] == i]) for i, v in enumerate(weekday)]


if __name__ == '__main__':
    gc = GoogleCalendar()
    print(gc.one_week_boss_schedule_messages())
