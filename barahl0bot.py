import util
import re
from database import Barahl0botDatabase
from settings import Barahl0botSettings
from vkontakte import VkontakteInfoGetter
from structures import Album
from telegram.ext import Updater, CommandHandler, ConversationHandler, Handler, MessageHandler, Filters
import telegram.ext
from enum import Enum


__author__ = 'fut33v'

_SETTINGS = Barahl0botSettings('settings.json')
_TOKEN_TELEGRAM = _SETTINGS.token_telegram
_CHANNEL = _SETTINGS.channel
_DATABASE = Barahl0botDatabase(_CHANNEL)
_VK_INFO_GETTER = VkontakteInfoGetter(_SETTINGS.token_vk)

REGEXP_ALBUM = re.compile("http[s]?://vk.com/album(-?\d*)_(\d*)")


def start_handler(update, context):
    response = """
    
    С помощью этого бота можно: 
    
    + добавить объявление на канал *@barahlochannel*, 
    + узнать список альбомов-источников канала. 

    *Github:* https://github.com/fut33v/barahl0bot

    *Техподдержка:* @fut33v
    
"""

    context.bot.send_message(update.effective_chat.id, response, parse_mode=telegram.ParseMode.MARKDOWN)


def get_albums_handler(update, context):
    response = "Сегодня без альбомов, братан."
    albums = _DATABASE.get_albums_list()
    if albums:
        response = ""
        for a in albums:
            response += a.build_url() + "\n"

    context.bot.send_message(update.effective_chat.id, response)


def add_album_handler(update, context):
    if len(context.args) == 0:
        return
    for album_candidate in context.args:
        print(album_candidate)
        m = REGEXP_ALBUM.match(album_candidate)
        if m:
            album = Album(m.group(1), m.group(2))
            if _DATABASE.is_album_in_table(album):
                response = "Не, такой альбом ({}) есть уже.".format(album_candidate)
            else:
                # add album
                _VK_INFO_GETTER.update_album_info(album)
                _DATABASE.insert_album(album)
                response = "Альбом <b>{}</b> добавлен.".format(album.title)
        else:
            response = "Не удалось распарсить ссылку <s>({})</s>".format(album_candidate)

        context.bot.send_message(update.effective_chat.id, response, parse_mode=telegram.ParseMode.HTML)


def remove_album_handler(update, context):
    if len(context.args) == 0:
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
                response = "Удалил."
        else:
            response = "Не удалось распарсить ссылку <s>({}</s>)".format(album_candidate)

        context.bot.send_message(update.effective_chat.id, response, parse_mode=telegram.ParseMode.HTML)


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
    context.bot.send_photo(chat_id='@'+_CHANNEL, photo=photo_message.photo[-1].file_id, caption=description[:1024])

    message = "Товар размещен в барахолке."
    context.bot.send_message(update.effective_chat.id, message)

    return ConversationHandler.END


def cancel_handler(update, context):
    return ConversationHandler.END


if __name__ == "__main__":
    updater = Updater(_TOKEN_TELEGRAM, use_context=True)
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
                            fallbacks=[CommandHandler('cancel', cancel_handler)],)
    )

    updater.start_polling()
    updater.idle()

