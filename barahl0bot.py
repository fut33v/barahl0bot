import datetime
import logging
import os
import re
import sys

import telegram.ext
from telegram.ext import Updater, CommandHandler
from vk_api.exceptions import ApiError

from bullshit.database import PostgreBarahlochDatabase
from bullshit.settings import Barahl0botSettings
from bullshit.structures import Album
from bullshit.vkontakte import VkontakteInfoGetter

__author__ = 'fut33v'

_LOGGER = logging.getLogger("barahl0bot")
_LOGS_DIR = 'log'
_FH_DEBUG = None
_FH_ERROR = None

REGEXP_ALBUM = re.compile("http[s]?://vk.com/album(-?\d*)_(\d*)")
REGEXP_ONLY_DIGITS = re.compile(r'^\d*$')


def start_handler(update, context):
    message_text = """
    
С помощью этого бота можно: 
    
+ узнать список альбомов-источников канала. 

*Github:* https://github.com/fut33v/barahl0bot

*Техподдержка:* @fut33v
    
""".format(channel=_CHANNEL)

    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=message_text,
                             parse_mode=telegram.ParseMode.MARKDOWN)


def get_albums_handler(update, context):
    response = "Сегодня без альбомов, братан."
    albums = _DATABASE.get_albums_list()
    if albums:
        response = ""
        for a in albums:
            response += a.build_url() + "\n"

    context.bot.send_message(update.effective_chat.id, response, disable_web_page_preview=True)


def add_album_handler(update, context):
    if len(context.args) == 0:
        return
    if update.effective_user.username not in _SETTINGS.admins:
        return
    for album_candidate in context.args:
        m = REGEXP_ALBUM.match(album_candidate)
        if m:
            album = Album(m.group(1), m.group(2))
            if _DATABASE.is_album_in_table(album):
                response = "Не, такой альбом ({}) есть уже.".format(album_candidate)
            else:
                try:
                    _VK_INFO_GETTER.update_album_info(album)
                    # insert group in table if not exists
                    if album.owner_id < 0:
                        if not _DATABASE.is_group_in_table_by_id(album.owner_id):
                            groups = _VK_INFO_GETTER.get_groups([abs(album.owner_id)])
                            if groups:
                                _DATABASE.insert_group(groups[0])
                    # insert album
                    _DATABASE.insert_album(album)
                    response = "Альбом <b>{}</b> добавлен.\n".format(album.title, album_candidate)
                except ApiError as e:
                    response = "Код ошибки VK API {}: {}".format(e.error['error_code'], e.error['error_msg'])
        else:
            response = "Не удалось распарсить ссылку <s>({})</s>".format(album_candidate)

        context.bot.send_message(update.effective_chat.id, response, parse_mode=telegram.ParseMode.HTML)


def remove_album_handler(update, context):
    if len(context.args) == 0:
        return
    if update.effective_user.username not in _SETTINGS.admins:
        return
    for album_candidate in context.args:
        print(album_candidate)
        m = REGEXP_ALBUM.match(album_candidate)
        if m:
            album = Album(m.group(1), m.group(2))
            if not _DATABASE.is_album_in_table(album):
                response = "Такого альбома найдено не было."
            else:
                _DATABASE.delete_album(album)
                response = "Удалил альбом\n{}".format(album_candidate)
        else:
            response = "Не удалось распарсить ссылку <s>({}</s>)".format(album_candidate)

        context.bot.send_message(update.effective_chat.id, response, parse_mode=telegram.ParseMode.HTML)


def set_logger_handlers(name):
    now = datetime.datetime.now()
    now = now.strftime("%d_%m_%Y")

    formatter = logging.Formatter('%(levelname)s %(asctime)s %(message)s')
    log_filename = _LOGS_DIR + "/{}_{}_debug.log".format(name, now)
    fh_debug = logging.FileHandler(log_filename)
    fh_debug.setLevel(logging.DEBUG)
    fh_debug.setFormatter(formatter)
    _LOGGER.addHandler(fh_debug)
    global _FH_DEBUG
    _FH_DEBUG = fh_debug


def error(update, context):
    """Log Errors caused by Updates."""
    _LOGGER.warning('Update "%s" caused error "%s"', update, context.error)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("give me json with settings as argument!")
        exit(-1)

    settings_filename = sys.argv[1]
    _SETTINGS = Barahl0botSettings(settings_filename)
    _TOKEN_TELEGRAM = _SETTINGS.token_telegram
    _CHANNEL = _SETTINGS.channel
    _DATABASE = PostgreBarahlochDatabase(_CHANNEL)
    _VK_INFO_GETTER = VkontakteInfoGetter(_SETTINGS.token_vk)

    if not _SETTINGS.storage_vk:
        _LOGGER.error("No VK storage for Telegram photos specified")
        exit(-1)
    _VK_TMP_PHOTOS_PATH = _SETTINGS.storage_vk['custom_path']

    if not os.path.exists(_VK_TMP_PHOTOS_PATH):
        os.mkdir(_VK_TMP_PHOTOS_PATH)

    logger_file_name = "{}_{}".format("bot", _CHANNEL)
    set_logger_handlers(logger_file_name)

    updater = Updater(_TOKEN_TELEGRAM, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', start_handler))
    dispatcher.add_handler(CommandHandler('getalbums', get_albums_handler))
    dispatcher.add_handler(CommandHandler('addalbum', add_album_handler))
    dispatcher.add_handler(CommandHandler('removealbum', remove_album_handler))

    dispatcher.add_error_handler(error)

    updater.start_polling()
    updater.idle()
