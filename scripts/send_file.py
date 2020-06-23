from settings import Barahl0botSettings
import sys
import os
import telegram
from telegram.bot import Bot

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("args: settings.json filename channel_name")
        exit(-1)

    settings_filename = sys.argv[1]
    filename_to_send = sys.argv[2]
    channel_name = sys.argv[3]

    _SETTINGS = Barahl0botSettings(settings_filename)

    bot = Bot(token=_SETTINGS.token_telegram)

    with open(filename_to_send, "rb") as f:
        filename = os.path.basename(filename_to_send)
        bot.send_document(chat_id='@'+channel_name, document=f, filename=filename)




