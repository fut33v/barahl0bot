from os import path
import re
import sys
import datetime
import logging
from functools import partial
from enum import Enum, IntEnum, auto

from database import Barahl0botDatabase
from settings import Barahl0botSettings
from vkontakte import VkontakteInfoGetter
from structures import Album, Group

from telegram.ext import \
    Updater, CommandHandler, ConversationHandler, Handler, MessageHandler, Filters, CallbackQueryHandler
import telegram.ext
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from vk_api.exceptions import ApiError

__author__ = 'fut33v'

_LOGGER = logging.getLogger("barahl0bot")
_LOGS_DIR = 'log'
_FH_DEBUG = None
_FH_ERROR = None

REGEXP_ALBUM = re.compile("http[s]?://vk.com/album(-?\d*)_(\d*)")


def start_handler(update, context):
    response = """
    
    С помощью этого бота можно: 
    
    + добавить объявление на канал *@{channel}* (/postitem), 
    + узнать список альбомов-источников канала. 

    *Github:* https://github.com/fut33v/barahl0bot

    *Техподдержка:* @fut33v
    
""".format(channel=_CHANNEL)

    context.bot.send_message(update.effective_chat.id, response, parse_mode=telegram.ParseMode.MARKDOWN)


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


class UserState(Enum):
    CHILLING = 0
    WAITING_FOR_CATEGORY = 1
    WAITING_FOR_SUBCATEGORY = 2
    WAITING_FOR_PHOTO = 3
    WAITING_FOR_TEXT = 4
    WAITING_FOR_APPROVE = 5


class CategoryEnum(IntEnum):
    ROAD_CX_GRAVEL = 1
    FIXED_SINGLE = 2


class CategoryStringEnum(Enum):
    ROAD_CX_GRAVEL = "Road, CX, Gravel, Touring - весь мультиспид."
    FIXED_SINGLE = "Fixed Gear, Single Speed - фиксы и трещотки."


class SubCategoryEnum(IntEnum):
    BICYCLE = 1
    COMPONENTS = 2
    WHEELS = 3
    WHEELS_COMPONENTS = 4
    CLOTHES = 5
    SHOES = 6
    HELMETS = 7
    ACCESSORIES = 8
    BAGS = 9


class SubCategoryStringEnum(Enum):
    BICYCLE = "Велосипед - велосипед  в полной комплектации"
    COMPONENTS = "Компоненты - рама, вилка и другие компоненты"
    WHEELS = "Колеса - собранные колеса"
    WHEELS_COMPONENTS = "Компоненты колес - обода, втулки, спицы, покрышки, камеры"
    CLOTHES = "Одежда - джерси, кепки, велошорты, носки"
    SHOES = "Обувь - велотуфли"
    HELMETS = "Шлемы - защитные каски, шлемесы"
    ACCESSORIES = "Аксессуары - очки, фонарики, насосы, велозамки, бутылки"
    BAGS = "Сумки - байкпакинг и прочие велоштаны"


ACTIVE_USERS = {}
MESSAGE_ID = {}


def post_item_handler(update, context):
    message = """
🚴‍♂️ Первым делом разберемся с категорией товара. Их немного, но они упростят поиск в канале.
Выбери ту категорию, которая наиболее точно подходит тебе. 

*Road, CX, Gravel, Touring* - весь мультиспид. 
*Fixed Gear, Single Speed* - фиксы и трещотки. 
"""
    keyboard = [[InlineKeyboardButton("ROAD/CX/Gravel", callback_data=str(int(CategoryEnum.ROAD_CX_GRAVEL))),
                 InlineKeyboardButton("Fixed gear/Single speed", callback_data=str(int(CategoryEnum.FIXED_SINGLE)))]]

    reply_markup = InlineKeyboardMarkup(keyboard)

    message = context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=message, reply_markup=reply_markup, parse_mode=telegram.ParseMode.MARKDOWN)

    MESSAGE_ID[update.effective_chat.id] = message.message_id

    return UserState.WAITING_FOR_CATEGORY


SUBCATEGORY_TEXT = """
Теперь выбери подкатегорию:

*Велосипед* - велосипед в полной комплектации. 
*Компоненты* - рама, вилка и другие компоненты. 
*Колеса* - собранные колеса. 
*Компоненты колес* - обода, втулки, спицы, покрышки, камеры. 
*Одежда* - джерси, кепки, велошорты, носки. 
*Обувь* - велотуфли. 
*Шлемы* - защитные каски. 
*Аксессуары* - очки, фонарики, насосы, велозамки, бутылки. 
*Сумки* - байкпакинг.
"""


def post_item_process_category(update, context, category):
    keyboard = [
        [InlineKeyboardButton("Велосипед", callback_data=str(int(SubCategoryEnum.BICYCLE))),
         InlineKeyboardButton("Компоненты", callback_data=str(int(SubCategoryEnum.COMPONENTS)))],
        [InlineKeyboardButton("Колеса", callback_data=str(int(SubCategoryEnum.WHEELS))),
         InlineKeyboardButton("Компоненты колес", callback_data=str(int(SubCategoryEnum.WHEELS_COMPONENTS)))],

        [InlineKeyboardButton("Одежда", callback_data=str(int(SubCategoryEnum.CLOTHES))),
         InlineKeyboardButton("Обувь", callback_data=str(int(SubCategoryEnum.SHOES)))],

        [InlineKeyboardButton("Шлемы", callback_data=str(int(SubCategoryEnum.HELMETS))),
         InlineKeyboardButton("Аксессуары", callback_data=str(int(SubCategoryEnum.ACCESSORIES))),
         InlineKeyboardButton("Сумки", callback_data=str(int(SubCategoryEnum.BAGS)))]]

    reply_markup = InlineKeyboardMarkup(keyboard)

    prefix_text = "Ты выбрал категорию *{}*\n".format(CategoryStringEnum[category.name].value)

    message_id_to_delete_keyboard = MESSAGE_ID[update.effective_chat.id]
    context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id,
                                          reply_markup=None, message_id=message_id_to_delete_keyboard)

    message_text = prefix_text + SUBCATEGORY_TEXT
    message = context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=message_text, reply_markup=reply_markup,
                                       parse_mode=telegram.ParseMode.MARKDOWN)

    MESSAGE_ID[update.effective_chat.id] = message.message_id

    return UserState.WAITING_FOR_SUBCATEGORY


def postitem_sub(update, context, subcategory):
    message_text = """
📷 Пришли фотографию товара. 
Можно отправить несколько фотографий как альбом в одном сообщении но при этом не более *10 штук*. 
"""

    prefix_text = "Ты выбрал подкатегорию *{}*\n".format(SubCategoryStringEnum[subcategory.name].value)
    message_text = prefix_text + message_text
    message_id_to_delete_keyboard = MESSAGE_ID[update.effective_chat.id]
    context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id,
                                          reply_markup=None, message_id=message_id_to_delete_keyboard)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=message_text, parse_mode=telegram.ParseMode.MARKDOWN)
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
    context.bot.send_photo(chat_id='@' + _CHANNEL, photo=photo_message.photo[-1].file_id, caption=description[:1024])

    message = "Товар размещен в барахолке."
    context.bot.send_message(update.effective_chat.id, message)

    return ConversationHandler.END


def cancel_handler(update, context):
    return ConversationHandler.END


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


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("give me json with settings as argument!")
        exit(-1)

    settings_filename = sys.argv[1]
    _SETTINGS = Barahl0botSettings(settings_filename)
    _TOKEN_TELEGRAM = _SETTINGS.token_telegram
    _CHANNEL = _SETTINGS.channel
    _DATABASE = Barahl0botDatabase(_CHANNEL)
    _VK_INFO_GETTER = VkontakteInfoGetter(_SETTINGS.token_vk)

    logger_file_name = "{}_{}".format("bot", _CHANNEL)
    set_logger_handlers(logger_file_name)

    updater = Updater(_TOKEN_TELEGRAM, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', start_handler))
    dispatcher.add_handler(CommandHandler('getalbums', get_albums_handler))
    dispatcher.add_handler(CommandHandler('addalbum', add_album_handler))
    dispatcher.add_handler(CommandHandler('removealbum', remove_album_handler))

    dispatcher.add_handler(
        ConversationHandler(entry_points=[CommandHandler('postitem', post_item_handler)],
                            states={
                                UserState.WAITING_FOR_CATEGORY: [
                                    CallbackQueryHandler(
                                        partial(post_item_process_category, category=CategoryEnum.ROAD_CX_GRAVEL),
                                        pattern='^' + str(int(CategoryEnum.ROAD_CX_GRAVEL)) + '$'),
                                    CallbackQueryHandler(
                                        partial(post_item_process_category, category=CategoryEnum.FIXED_SINGLE),
                                        pattern='^' + str(int(CategoryEnum.FIXED_SINGLE)) + '$')
                                ],
                                UserState.WAITING_FOR_SUBCATEGORY: [
                                    CallbackQueryHandler(partial(postitem_sub, subcategory=SubCategoryEnum.BICYCLE),
                                                         pattern='^' + str(int(SubCategoryEnum.BICYCLE)) + '$'),
                                    CallbackQueryHandler(partial(postitem_sub, subcategory=SubCategoryEnum.COMPONENTS),
                                                         pattern='^' + str(int(SubCategoryEnum.COMPONENTS)) + '$'),
                                ],
                                UserState.WAITING_FOR_PHOTO: [MessageHandler(
                                    callback=add_item_process_photo, filters=Filters.photo)],
                                UserState.WAITING_FOR_TEXT: [MessageHandler(
                                    callback=add_item_process_text, filters=Filters.text)],
                                UserState.WAITING_FOR_APPROVE: [CommandHandler('done', add_item_process_approve)]
                            },
                            fallbacks=[CommandHandler('cancel', cancel_handler)], )
    )

    updater.start_polling()
    updater.idle()
