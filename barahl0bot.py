# coding=utf-8
import re

from util import bot_util

from telegram.ext import Updater, CommandHandler, ConversationHandler, Handler, MessageHandler, Filters
import telegram.ext
from enum import Enum


__author__ = 'fut33v'

DATA_DIRNAME = "data/"
TOKEN_FILENAME = DATA_DIRNAME + "token"
ALBUMS_FILENAME = DATA_DIRNAME + 'albums'
ADMIN_FILENAME = DATA_DIRNAME + 'admin'
CHANNEL_FILENAME = DATA_DIRNAME + 'channel'

admins = None
with open(ADMIN_FILENAME) as admins_file:
    lines = admins_file.readlines()
    if lines:
        admins = list()
        for line in lines:
            admins.append(line[:-1])
        admins = set(admins)


CHANNEL = bot_util.read_one_string_file(CHANNEL_FILENAME)
REGEXP_ALBUM = re.compile("http[s]?://vk.com/album(-?\d*_\d*)")


def start_handler(update, context):
    response = """
    
    С помощью этого бота можно: 
    
    + добавить объявление на канал *@barahlochannel*, 
    + узнать список альбомов источников канала. 

    *Github:* https://github.com/fut33v/barahl0bot

    *Техподдержка:* @fut33v
    
"""

    context.bot.send_message(update.effective_chat.id, response, parse_mode=telegram.ParseMode.MARKDOWN)


def get_albums_handler(update, context):
    response = "Сегодня без альбомов, братан"
    albums = bot_util.read_lines(ALBUMS_FILENAME)
    if albums:
        response = ""
        for a in albums:
            response += "https://vk.com/album" + a

    context.bot.send_message(update.effective_chat.id, response)


def add_album_handler(update, context):
    if len(context.args) == 0:
        return
    for album_candidate in context.args:
        print(album_candidate)
        m = REGEXP_ALBUM.match(album_candidate)
        if m:
            album = m.group(1)
            if bot_util.check_file_for_string(ALBUMS_FILENAME, album + "\n"):
                open(ALBUMS_FILENAME, 'a').write(album + "\n")
                response = "Альбом добавлен."
            else:
                response = "Не, такой альбом ({}) есть уже.".format(album_candidate)
        else:
            response = "Не удалось распарсить ссылку ({})".format(album_candidate)

        context.bot.send_message(update.effective_chat.id, response)


def remove_album_handler(update, context):
    if len(context.args) == 0:
        return
    for album_candidate in context.args:
        print(album_candidate)
        m = REGEXP_ALBUM.match(album_candidate)
        if m:
            album = m.group(1)
            if bot_util.check_file_for_string(ALBUMS_FILENAME, album + "\n"):
                response = "Такого альбома найдено не было."
            else:
                temp = []
                with open(ALBUMS_FILENAME) as fp:
                    temp = fp.read().split("\n")
                    temp = [x for x in temp if x != str(album) and x != ""]
                with open(ALBUMS_FILENAME, 'w') as fp:
                    for item in temp:
                        fp.write("%s\n" % item)
                response = "Удалил."
        else:
            response = "Не удалось распарсить ссылку ({})".format(album_candidate)

        context.bot.send_message(update.effective_chat.id, response)


class UserState(Enum):
    CHILLING = 0
    WAITING_FOR_PHOTO = 1
    WAITING_FOR_TEXT = 2


ACTIVE_USERS = {}


def add_item_handler(update, context):
    message = "Пришли фото или альбом."
    context.bot.send_message(update.effective_chat.id, message)
    return UserState.WAITING_FOR_PHOTO


def add_item_chilling(update, context):
    return ""


def add_item_waiting_for_photo(update, context):
    message = "Теперь пиши описание товара."
    context.bot.send_message(update.effective_chat.id, message)

    # save photo to some user related dictionary
    ACTIVE_USERS[update.effective_user] = update.effective_message

    return UserState.WAITING_FOR_TEXT


def add_item_waiting_for_text(update, context):
    description = update.effective_message.text
    # get photo for this user and send photo+desc to channel
    if update.effective_user.username:
        description = "@" + update.effective_user.username + "\n" + description
    photo_message = ACTIVE_USERS[update.effective_user]

    context.bot.send_photo(chat_id=CHANNEL, photo=photo_message.photo[-1].file_id, caption=description[:1024])
    # context.bot.send_message(CHANNEL, description)

    return ConversationHandler.END


def cancel_handler(update, context):
    return ""


if __name__ == "__main__":
    token = bot_util.read_one_string_file(TOKEN_FILENAME)
    print(token)
    updater = Updater(token, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', start_handler))
    dispatcher.add_handler(CommandHandler('getalbums', get_albums_handler))
    dispatcher.add_handler(CommandHandler('addalbum', add_album_handler))
    dispatcher.add_handler(CommandHandler('removealbum', remove_album_handler))

    additem_ch = CommandHandler('additem', add_item_handler)
    fallbacks = [CommandHandler('cancel', cancel_handler)]
    print(type(fallbacks))
    dispatcher.add_handler(
        ConversationHandler(entry_points=[additem_ch],
                            states={
                                UserState.CHILLING: [Handler(add_item_chilling)],
                                UserState.WAITING_FOR_PHOTO: [MessageHandler(
                                    callback=add_item_waiting_for_photo, filters=Filters.photo)],
                                UserState.WAITING_FOR_TEXT: [MessageHandler(
                                    callback=add_item_waiting_for_text, filters=Filters.text)]
                            },
                            fallbacks=[CommandHandler('cancel', cancel_handler)],
        )
    )

    updater.start_polling()
    updater.idle()

