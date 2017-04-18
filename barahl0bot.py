# coding=utf-8
import re

from util import bot_util
from telegram_bot.telegram_bot import TelegramBot

__author__ = 'fut33v'

DATA_DIRNAME = "data/"
TOKEN_FILENAME = DATA_DIRNAME + "token"
ALBUMS_FILENAME = DATA_DIRNAME + 'albums'

REGEXP_ALBUM = re.compile("http[s]?://vk.com/album(-?\d*_\d*)")


class BarahloBot(TelegramBot):
    def __init__(self, token, name):
        TelegramBot.__init__(self, token, name)

    def _process_message(self, user_id, chat_id, text):
        if text == '/start':
            response = """
                Я буду присылать тебе новые товары из велобарахолок.
                Техподдержка: @fut33v
            """
        else:
            response = "Чего блять?"
            if user_id == "fut33v":
                command = text.split(' ')
                if len(command) == 2:
                    if command[0] == "/addalbum":
                        m = REGEXP_ALBUM.match(command[1])
                        if m:
                            album = m.group(1) + "\n"
                            # album = command[1] + "\n"
                            if bot_util.check_file_for_string(ALBUMS_FILENAME, album):
                                open(ALBUMS_FILENAME, 'a').write(album)
                                response = "Альбом добавлен"
                            else:
                                response = "Не, такой альбом есть уже"

        if response:
            success = self.send_response(chat_id, response=response, markdown=True)
            return success
        return False

    def _get_start_message(self):
        return """
        Я буду присылать тебе новые товары из велобарахолок.
        Техподдержка: @fut33v
        """


if __name__ == "__main__":
    t = bot_util.read_one_string_file(TOKEN_FILENAME)
    bot = BarahloBot(t, name="barahl0bot")
    bot.start_poll()
