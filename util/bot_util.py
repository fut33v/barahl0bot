import calendar
import json
import os
import urllib.error
import urllib.error
import urllib.parse
import urllib.parse
import urllib.request
import urllib.request

from datetime import datetime
from datetime import timezone
import pytz

from functools import partial

__author__ = 'fut33v'


def urlopen(url, data=None):
    try:
        if data is not None:
            data = urllib.parse.urlencode(data)
            # print data
            urllib.request.urlopen(url, data)
            return True
        else:
            response = urllib.request.urlopen(url)
            data = response.read()
            return data
    except urllib.error.HTTPError as e:
        print(("HTTPError", e, url, data))
    except urllib.error.URLError as e:
        print(("URLError", e, url, data))
    except Exception as e:
        print(("Exception", e, url, data))
    return False


def get_unix_timestamp():
    d = datetime.utcnow()
    return calendar.timegm(d.utctimetuple())


def get_photo_time_from_unix_timestamp(_timestamp):
    moscow = pytz.timezone('Europe/Moscow')
    dt = datetime.fromtimestamp(_timestamp, moscow)
    return "{:02d}.{:02d}.{} {:02d}:{:02d}".format(dt.day, dt.month, dt.year, dt.hour, dt.minute)


def read_one_string_file(filename):
    try:
        f = open(filename, 'r')
        s = f.read()
        s = s.replace('\n', '')
        s = s.replace('\r', '')
        return s
    except IOError:
        return None


def read_lines(filename):
    try:
        f = open(filename, 'r')
        s = f.readlines()
        return s
    except IOError:
        return None


def check_file_for_string(filename, string):
    if not os.path.exists(filename):
        return True
    f = open(filename, 'r')
    lines = f.readlines()
    for line in lines:
        if line == string:
            return False
    return True


def append_string_to_file(file_name, string):
    open(file_name, 'a').write(string)


def create_dir_if_not_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def load_json_file(filename):
    json_f = open(filename, 'r')
    j = json_f.read()
    json_f.close()
    json_obj = json.loads(j)
    return json_obj


json_pretty_dumps = partial(
    json.dumps,
    sort_keys=True,
    indent=4,
    separators=(',', ': ')
)


def save_json_file(filename, data):
    json_txt = json_pretty_dumps(data)
    json_f = open(filename, 'w')
    json_f.write(json_txt)
    json_f.close()


def tg_date_to_mysql(_date):
    ds = _date.split(' ')
    dmy = ds[0].split('.')
    hms = ds[1]
    # YYYY-MM-DD hh:mm:ss
    return "{}-{}-{} {}".format(dmy[2], dmy[1], dmy[0], hms)
