# coding=utf-8
import re

from util import bot_util

from telegram.ext import Updater, CommandHandler, ConversationHandler, Handler, MessageHandler, Filters
import telegram.ext
from enum import Enum


__author__ = 'fut33v'

DATA_DIRNAME = "data/"
ALBUMS_FILENAME = DATA_DIRNAME + 'albums'

REGEXP_ALBUM = re.compile("http[s]?://vk.com/album(-?\d*_\d*)")

_SETTINGS_JSON_FILENAME = "settings.json"
SETTINGS = bot_util.load_json_file(_SETTINGS_JSON_FILENAME)
ADMINS = set(SETTINGS['admins'])
CHANNELS = set(SETTINGS['channels'])
ERROR_CHANNEL = SETTINGS['error_channel']
TOKEN = SETTINGS['token']
TOKEN_VK = SETTINGS['token_vk']
SECONDS_TO_SLEEP = SETTINGS['seconds_to_sleep']


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
    WAITING_FOR_TEXT = 2,
    WAITING_FOR_APPROVE = 3


ACTIVE_USERS = {}


def add_item_handler(update, context):
    message = "Пришлите фото или альбом.\n\nИли нажмите /cancel для отмены."
    context.bot.send_message(update.effective_chat.id, message)
    return UserState.WAITING_FOR_PHOTO


def add_item_process_photo(update, context):
    # save photo to some user related dictionary
    ACTIVE_USERS[update.effective_user] = {"photo": update.effective_message}

    message = "Теперь пришлите описание товара.\n\nИли нажмите /cancel для отмены."
    context.bot.send_message(update.effective_chat.id, message)

    return UserState.WAITING_FOR_TEXT


def add_item_process_text(update, context):
    description = update.effective_message.text

    if description == '/cancel':
        return ConversationHandler.END

    if update.effective_user.username:
        description = "@" + update.effective_user.username + "\n" + description

    # get photo for this user and send photo+desc to channel
    ACTIVE_USERS[update.effective_user]["description"] = description

    message = "Нажмите */done* для подтверждения или */cancel* для отмены."
    context.bot.send_message(update.effective_chat.id, message, parse_mode=telegram.ParseMode.MARKDOWN)

    return UserState.WAITING_FOR_APPROVE


def add_item_process_approve(update, context):
    description = ACTIVE_USERS[update.effective_user]["description"]
    photo_message = ACTIVE_USERS[update.effective_user]["photo"]
    for channel in CHANNELS:
        context.bot.send_photo(chat_id=channel, photo=photo_message.photo[-1].file_id, caption=description[:1024])

    message = "Товар размещен в барахолке."
    context.bot.send_message(update.effective_chat.id, message)

    return ConversationHandler.END


def cancel_handler(update, context):
    return ConversationHandler.END


def post_to_channel_html(message, channel):
    bot = telegram.Bot(token=TOKEN)
    return bot.send_message(channel, message, parse_mode=telegram.ParseMode.HTML)


def post_to_error_channel(message):
    bot = telegram.Bot(token=TOKEN)
    return bot.send_message(ERROR_CHANNEL, message, parse_mode=telegram.ParseMode.MARKDOWN)


if __name__ == "__main__":
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', start_handler))
    dispatcher.add_handler(CommandHandler('getalbums', get_albums_handler))
    dispatcher.add_handler(CommandHandler('addalbum', add_album_handler))
    dispatcher.add_handler(CommandHandler('removealbum', remove_album_handler))

    dispatcher.add_handler(
        ConversationHandler(entry_points=[CommandHandler('additem', add_item_handler)],
                            states={
                                UserState.WAITING_FOR_PHOTO: [MessageHandler(
                                    callback=add_item_process_photo, filters=Filters.photo)],
                                UserState.WAITING_FOR_TEXT: [MessageHandler(
                                    callback=add_item_process_text, filters=Filters.text)],
                                UserState.WAITING_FOR_APPROVE: [CommandHandler('done', add_item_process_approve)]
                            },
                            fallbacks=[CommandHandler('cancel', cancel_handler)],
        )
    )

    updater.start_polling()
    updater.idle()

