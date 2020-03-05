# coding=utf-8

import barahl0bot
from util import bot_util

import telegram.ext

__author__ = 'fut33v'

_CHATS_FILE = barahl0bot.DATA_DIRNAME + 'chats'

def broadcast_message(message):
    t = bot_util.read_one_string_file(barahl0bot.TOKEN_FILENAME)
    bot = telegram.Bot(token=t)
    lines = open(_CHATS_FILE, 'r').readlines()
    for chat_id in lines:
        # chat_id = int(chat_id)
        bot.send_message(chat_id, message, parse_mode=telegram.ParseMode.HTML)


if __name__ == "__main__":
    m = "test"
    broadcast_message(m)

