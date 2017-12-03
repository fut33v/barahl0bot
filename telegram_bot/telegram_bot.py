import json
import re
import time
import urllib
import urllib2

from util import bot_util
import telegram_bot_protocol

__author__ = 'fut33v'


class TelegramBot:
    _URL_COMMON_TEMPLATE = "https://api.telegram.org/bot%s/"
    _COMMAND_START = "/start"
    _COMMAND_HELP = "/help"
    _DATA_DIRNAME = "data/"
    _PREVIOUS_UPDATE_DATE_FILENAME = _DATA_DIRNAME + 'previous_update_date'

    def __init__(self, token, name, botan_token=None):
        self._token = token
        self.name = name

        self._commands_no_parameter = []

        self._commands_with_parameter = []
        self._commands_with_parameters_regexps_dict = {}

        self._previous_update_date = self._read_previous_update_date()

        self._url_common = self._URL_COMMON_TEMPLATE % token
        if self._url_common is None:
            raise Exception("Error while reading token file")

        self._url_get_updates = self._url_common + "getUpdates"
        self._url_send_message = self._url_common + "sendMessage"
        self._botan_token = botan_token

        bot_util.create_dir_if_not_exists(self._DATA_DIRNAME)
        self._chats_file = self._DATA_DIRNAME + "chats"
        self._usernames_file = self._DATA_DIRNAME + "usernames"

    def start_poll(self):
        last = 0
        while True:
            r = bot_util.urlopen(self._url_get_updates + "?offset=%s" % (last + 1))
            if r:
                try:
                    r = json.loads(r)
                except ValueError as e:
                    print "Error while polling (json.loads):", e
                    continue
                if 'result' in r:
                    for update in r['result']:
                        if len(update) > 0:
                            print update
                        if 'message' in update:
                            message = update['message']
                            if 'date' in message:
                                date = message['date']
                                if self._previous_update_date >= int(date):
                                    continue
                                if 'update_id' in update:
                                    last = int(update["update_id"])
                                self._process_update(update)
                                previous_update_date = int(date)
                                self._write_previous_update_date(previous_update_date)
            time.sleep(3)

    def _process_update(self, update):
        if update is None:
            return
        message = telegram_bot_protocol.get_message(update)
        if message:

            chat_id = telegram_bot_protocol.get_chat_id(message)

            text = telegram_bot_protocol.get_text(message)

            if chat_id and text:
                username = ""
                if 'from' in message:
                    from_ = message['from']
                    if 'username' in from_:
                        username = str(from_['username'])
                        if bot_util.check_file_for_string(self._usernames_file, username + "\n"):
                            open(self._usernames_file, 'a').write(username + "\n")
                self._process_message(username, chat_id, text)

    def _process_message(self, user_id, chat_id, text):
        raise NotImplemented

    def send_response(self, chat_id, response, markdown=False, html=False):
        if response is None or chat_id is None or response == '':
            return False
        if isinstance(response, unicode):
            response = response.encode('utf-8')
        d = {
            'chat_id': chat_id,
            'text': response,
        }
        if not (markdown and html):
            if markdown is True:
                d['parse_mode'] = "Markdown"
            if html is True:
                d['parse_mode'] = "HTML"

        return bot_util.urlopen(self._url_send_message, data=d)

    def send_to_channel(self, channel_id, response):
        if response is None or channel_id is None or response == '':
            return False
        data = {
            'text': response,
        }
        data = urllib.urlencode(data) + "&chat_id=@" + channel_id
        urllib2.urlopen(self._url_send_message, data)

    def _read_previous_update_date(self):
        u = bot_util.read_one_string_file(self._PREVIOUS_UPDATE_DATE_FILENAME)
        if u == '' or u is None:
            return 0
        return int(u)

    def _write_previous_update_date(self, d):
        open(self._PREVIOUS_UPDATE_DATE_FILENAME, 'w').write(str(d))


if __name__ == "__main__":
    t = TelegramBot("", "name")
