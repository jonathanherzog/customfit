import datetime

import pytz
from django.conf import settings

# How many days the user has to redo their pattern
REDO_DEADLINE_IN_DAYS = 90

# When this deadline was started (so we allow the users N days after creation
# *or* this date, whichever is later)
_tz = pytz.timezone(settings.TIME_ZONE)
REDO_DEADLINE_START = datetime.datetime(2018, 3, 20, 0, 0, 0, 0, _tz)
