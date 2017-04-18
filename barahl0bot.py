# coding=utf-8

from util import bot_util
from telegram_bot.telegram_bot import TelegramBot

__author__ = 'fut33v'

TOKEN_FILENAME = "data/token"


class BarahloBot(TelegramBot):
    def __init__(self, token, name):
        TelegramBot.__init__(self, token, name)

    def _process_message(self, chat_id, text):
        if text == '/start':
            response = """
                Я буду присылать тебе новые товары из велобарахолок.
                Техподдержка: @fut33v
            """
        else:
            response = "Чего блять?"
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
