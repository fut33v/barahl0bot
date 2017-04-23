# coding=utf-8
import re

from util import bot_util
from telegram_bot.telegram_bot import TelegramBot

__author__ = 'fut33v'

DATA_DIRNAME = "data/"
TOKEN_FILENAME = DATA_DIRNAME + "token"
ALBUMS_FILENAME = DATA_DIRNAME + 'albums'
ADMIN_FILENAME = DATA_DIRNAME + 'admin'

admins = None
with open(ADMIN_FILENAME) as admins_file:
    lines = admins_file.readlines()
    if lines:
        admins = list()
        for line in lines:
            admins.append(line[:-1])
        admins = set(admins)


REGEXP_ALBUM = re.compile("http[s]?://vk.com/album(-?\d*_\d*)")


class BarahloBot(TelegramBot):
    def __init__(self, token, name):
        TelegramBot.__init__(self, token, name)

    def _process_message(self, user_id, chat_id, text):
        if text == '/start':
            response = """
Я буду присылать тебе новые товары из велобарахолок.
Не надо мне ничего писать, я ничего тебе не отвечу, просто жди новых фоток.

Github: https://github.com/fut33v/barahl0bot

Техподдержка: @fut33v

Если я затупил, понажимай /start или пиши @fut33v
            """
        else:
            response = "Чего блять?"
            if text == "/getalbums":
                albums = bot_util.read_lines(ALBUMS_FILENAME)
                if albums:
                    response = ""
                    for a in albums:
                        response += "https://vk.com/album" + a
            # admin stuff
            if user_id in admins:
                command = text.split(' ')
                if len(command) == 2:
                    if command[0] == "/addalbum":
                        m = REGEXP_ALBUM.match(command[1])
                        if m:
                            album = m.group(1) + "\n"
                            if bot_util.check_file_for_string(ALBUMS_FILENAME, album):
                                open(ALBUMS_FILENAME, 'a').write(album)
                                response = "Альбом добавлен"
                            else:
                                response = "Не, такой альбом есть уже"
                elif len(command) == 1:
                    if command[0] == '/getchats':
                        response = str(len(bot_util.read_lines(self._chats_file)))
                    if command[0] == '/getusers':
                        response = ""
                        usernames = bot_util.read_lines(self._usernames_file)
                        for u in usernames:
                            response += "@" + u

        if response:
            success = self.send_response(chat_id, response=response)
            return success
        return False

if __name__ == "__main__":
    t = bot_util.read_one_string_file(TOKEN_FILENAME)
    bot = BarahloBot(t, name="barahl0bot")
    bot.start_poll()
