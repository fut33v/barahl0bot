# coding=utf-8

from util import bot_util
from telegram_bot.telegram_bot import TelegramBot

__author__ = 'fut33v'

TOKEN_FILENAME = "data/token"
BOTAN_TOKEN_FILENAME = "data/botan_token"
WEATHER_COM_TOKEN_FILENAME = "data/weather_com_token"


class BarahloBot(TelegramBot):
    def __init__(self, token, name, weather_com_token=None, botan_token=None):
        TelegramBot.__init__(self, token, name, botan_token)

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
    bot = BarahloBot(t, name="NovgorodWeatherBot")
    bot.start_poll()
