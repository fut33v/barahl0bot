# coding=utf-8

import barahl0bot
from util import bot_util

__author__ = 'fut33v'


def broadcast_message(message):
    t = bot_util.read_one_string_file(barahl0bot.TOKEN_FILENAME)
    bot = barahl0bot.BarahloBot(t, name="barahl0bot")
    lines = open(bot._chats_file, 'r').readlines()
    for l in lines:
        # l = int(l)
        bot.send_response(l, message)

if __name__ == "__main__":
    m = "test"
    broadcast_message(m)

    # t = bot_util.read_one_string_file(barahl0bot.TOKEN_FILENAME)
    # bot = barahl0bot.BarahloBot(t, name="barahl0bot")
    # bot.send_to_channel("barahlochannel", "test")

