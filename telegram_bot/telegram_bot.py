import json
import re
import time

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
        self.add_command_no_parameter(self._COMMAND_START)
        self.add_command_no_parameter(self._COMMAND_HELP)

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
        self.chats_file = self._DATA_DIRNAME + "chats"

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
                # print r["result"]
                for update in r["result"]:
                    if len(update) > 0:
                        print update
                    if self._previous_update_date >= int(update["message"]["date"]):
                        continue
                    last = int(update["update_id"])
                    self._process_update(update)
                    previous_update_date = int(update["message"]["date"])
                    self._write_previous_update_date(previous_update_date)
            time.sleep(3)

    def _process_update(self, update):
        if update is None:
            return
        message = telegram_bot_protocol.get_message(update)
        if message:

            chat_id = telegram_bot_protocol.get_chat_id(message)
            chat_id_string = str(chat_id) + "\n"
            if bot_util.check_file_for_string(self.chats_file, chat_id_string):
                open(self.chats_file, 'a').write(chat_id_string)

            text = telegram_bot_protocol.get_text(message)

            if chat_id and text:
                user_id = ""
                if 'from' in message:
                    from_ = message['from']
                    if 'username' in from_:
                        user_id = from_['username']
                self._process_message(user_id, chat_id, text)

    def _process_message(self, user_id, chat_id, text):
        raise NotImplemented

    def send_response(self, chat_id, response, markdown=False):
        if response is None or chat_id is None or response == '':
            return False
        if isinstance(response, unicode):
            response = response.encode('utf-8')
        d = {
            'chat_id': chat_id,
            'text': response,
        }
        if markdown is True:
            d['parse_mode'] = "Markdown"
        return bot_util.urlopen(self._url_send_message, data=d)

    def _read_previous_update_date(self):
        u = bot_util.read_one_string_file(self._PREVIOUS_UPDATE_DATE_FILENAME)
        if u == '' or None == u:
            return 0
        return int(u)

    def _write_previous_update_date(self, d):
        open(self._PREVIOUS_UPDATE_DATE_FILENAME, 'w').write(str(d))

    def _get_command_name_in_group(self, command_name):
        command_name_in_group = command_name + "@" + self.name
        return command_name_in_group

    def _check_message_for_command(self, text, command_name):
        return text == command_name or text == self._get_command_name_in_group(command_name)

    def add_command_no_parameter(self, command_name):
        command_name_in_group = self._get_command_name_in_group(command_name)
        self._commands_no_parameter.append(command_name)
        self._commands_no_parameter.append(command_name_in_group)

    def add_command_with_parameter(self, command_name):
        command_name_in_group = self._get_command_name_in_group(command_name)
        self._commands_with_parameter.append(command_name)
        self._commands_with_parameter.append(command_name_in_group)
        self._commands_with_parameters_regexps_dict[command_name] = re.compile(command_name + " (.*)")
        self._commands_with_parameters_regexps_dict[command_name_in_group] = re.compile(command_name_in_group + " (.*)")

    def _get_command_parameter(self, command_name, text):
        if command_name not in self._commands_with_parameters_regexps_dict:
            print "Command with name", command_name, "not command with parameters"
            return None
        r = self._commands_with_parameters_regexps_dict[command_name]
        m = r.match(text)
        if m is None:
            return None
        if m.group(1) != '':
            return m.group(1)
        else:
            return None

    def _get_start_message(self):
        return "Default /start message"


if __name__ == "__main__":
    t = TelegramBot("", "name")
    t.add_command_with_parameter("/lox")
    ret = t._get_command_parameter("/lox", "/lox abcd")
    print ret
    ret = t._get_command_parameter("/lox@name", "/lox@name abcd")
    print ret
