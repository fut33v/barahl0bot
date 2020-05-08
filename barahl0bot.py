import re
import datetime
import logging
import re
import sys
import html
from enum import Enum
from functools import partial

import telegram.ext
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, ConversationHandler, MessageHandler, Filters, CallbackQueryHandler
from vk_api.exceptions import ApiError

from database import Barahl0botDatabase
from settings import Barahl0botSettings
from structures import Album
from vkontakte import VkontakteInfoGetter
import util

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
    
    + добавить объявление на канал *@{channel}* (/postitem), 
    + узнать список альбомов-источников канала. 

    *Github:* https://github.com/fut33v/barahl0bot

    *Техподдержка:* @fut33v
    
""".format(channel=_CHANNEL)

    keyboard = [[InlineKeyboardButton(CallbackDataEnum.POSTITEM.value, callback_data=CallbackDataEnum.POSTITEM.name)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=message_text,
                                       reply_markup=reply_markup,
                                       parse_mode=telegram.ParseMode.MARKDOWN)

    save_message_id(update, message)


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


class Chat:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.user_id = None
        self.prev_message_id = None
        self.user_state = None

        self.parent_category = None
        self.category = None
        self.category_dict = {0: None, 1: None, 2: None}

        self.photo_message = None
        self.currency = None
        self.price = None
        self.ship = None
        self.city = None
        self.caption = None
        self.description = None

    def get_full_category_string(self):
        category_string = ""
        for c in self.category_dict.items():
            if c[1] is not None:
                category_string += c[1].value + "/"

        return category_string

    def get_hashtags(self):
        hashtags = ""
        for c in self.category_dict.items():
            if c[1] is not None:
                hashtags += "#" + c[1].name.lower() + " "
        return hashtags


class UserState(Enum):
    CHILLING = 0

    WAITING_FOR_CATEGORY = 1
    WAITING_FOR_PHOTO = 2
    WAITING_FOR_CURRENCY = 3
    WAITING_FOR_PRICE = 4
    WAITING_FOR_SHIP = 5
    WAITING_FOR_CITY = 6
    WAITING_FOR_CAPTION = 7
    WAITING_FOR_DESCRIPTION = 8
    WAITING_FOR_APPROVE = 9

    WAITING_FOR_BICYCLE = 20
    WAITING_FOR_COMPONENT = 21
    WAITING_FOR_WHEELS = 22
    WAITING_FOR_ACCESSORIES = 23
    WAITING_FOR_BAGS = 24
    WAITING_FOR_SERVICE = 25

    WAITING_FOR_SEATING = 31
    WAITING_FOR_PEDALS = 32
    WAITING_FOR_STEERING = 32


class CategoryEnum(Enum):
    BICYCLE = "Велосипед"
    COMPONENTS = "Компоненты"
    WHEELS = "Колеса и покрышки"
    SERVICE = "Обслуживание"
    ACCESSORIES = "Аксессуары"
    CLOTHES = "Одежда"
    SHOES = "Обувь"
    HELMETS = "Шлемы"
    BAGS = "Сумки"


class BicycleCategoryEnum(Enum):
    ROAD = "Шоссер"
    CYCLOCROSS = "Циклокросс"
    FIX = "Фикс"
    SINGLE = "Синглспид"
    GRAVEL = "Гревел"
    TOURING = "Туринг"


class ComponentCategoryEnum(Enum):
    FRAME = "Рама"
    FORK = "Вилка"
    BRAKES = "Тормоза"
    STEERING = "Рулевое управление"
    SEATING = "Седла и штыри"
    TRANSMISSION = "Трансмиссия"
    PEDALS = "Педали и шипы"


class SeatingCategoryEnum(Enum):
    SADDLES = "Седла"
    SEATPOST = "Подседел"
    SEATCLAMPS = "Зажим"


class PedalsCategoryEnum(Enum):
    PEDALS = "Педали"
    CLEATS = "Шипы"
    STRAPS = "Стрепы"
    TOECLIP = "Туклипсы"


class SteeringCategoryEnum(Enum):
    HANDLEBARS = "Рули"
    STEMS = "Выносы"
    HEADSETS = "Рулевые"
    TOPCAPS = "Топкепы"
    SPACERS = "Проставочные кольца"
    BARTAPES = "Обмотки"
    GRIPS = "Грипсы"


class WheelsCategoryEnum(Enum):
    WHEELS = "Колеса"
    HUBS = "Втулки"
    TIRES = "Покрышки"
    RIMS = "Обода"
    TUBES = "Камеры"
    SPOKES = "Спицы"


class ServiceCategoryEnum(Enum):
    PUMPS = "Насосы"
    TOOLS = "Инструменты"
    WORKSTAND = "Стойки и стенды"


class AccessoriesCategoryEnum(Enum):
    GLASSES = "Очки"
    LOCK = "Замки"
    LIGHT = "Фонари"
    BOTTLE = "Фляги и флягодержатели"
    COMPUTER = "Велокомпы"
    MUDGUARD = "Крылья"
    RACK = "Багажники"
    TRAINER = "Станки"


class BagsCategoryEnum(Enum):
    CASE = "Чехлы и боксы"
    BAUL = "Баулы"
    ROLLTOP = "Роллтопы"
    MESSENGER = "Мессенджеры"
    STEERING_BAG = "Нарульные сумки"
    WAIST_BAG = "Поясные сумки"


class PhotoOrAlbumEnum(Enum):
    PHOTO = "одна фотка"
    ALBUM = "альбом"


class CurrencyEnum(Enum):
    RUB = 'RUB ₽'
    USD = 'USD $'
    EUR = 'EUR €'
    UAH = 'UAH '


class ShippingEnum(Enum):
    DO_NOT_SHIP = "Не отправляю"
    WILL_SHIP_BY_CUSTOMER = "За счет покупателя"
    WILL_SHIP_SAINT = "За свой счёт"


class CallbackDataEnum(Enum):
    POSTITEM = 'Добавить товар'
    BACK = 'Назад'
    DONE = "Подтвердить"
    CANCEL = 'Отмена'
    CITY_OTHER = 'Другой'
    CITY = 'City'


CHATS_DICT = {}
POSTFIX_CANCEL = "\n/cancel для отмены."


def get_top_cities():
    return _DATABASE.get_top_cities(10)


def get_button_for_enum(enum_member):
    return InlineKeyboardButton(enum_member.value, callback_data=enum_member.name)


def keyboard_for_enum(enum):
    keyboard = []
    counter = 0
    row = []
    for e in enum:
        row.append(get_button_for_enum(e))
        if counter % 2 == 0:
            keyboard.append(row)
            row = []
        counter += 1
    return keyboard


def category_message_text(category=None):
    message_text = """
        🚴‍♂️ Категория. 

Выбери категорию, которая наиболее точно подходит тебе. 
Правильно выбранная категория поможет покупателю быстрее найти товар. 

👉🏻👉🏻 Категории *Велосипеды, Компоненты, Колеса и покрышки, Обслуживание, Аксессуары, Сумки* имеют подкатегории. 

🤙🏻🤙🏻 Подкатегории *Рулевое управление, Седла и штыри, Педали и шипы, Трансмиссия* имеют подкатегории. 

*Одежда* - джерси, бибы, кепки, рукава, носки, перчатки, куртки, бафы. 

*Обувь* - велотуфли, бахилы. 

*Шлемы* - шлемы, визоры.
"""
    if category:
        message_text = "{}\n ➡️ *{}*\n {}".format(message_text, category.value, POSTFIX_CANCEL)
    else:
        message_text = message_text + POSTFIX_CANCEL

    return message_text


def photo_message_text():
    message_text = """
📷 Пришли фотографию товара. 
Можно отправить только одну (пока) фотографию в одном сообщении. 
"""
    return message_text


def get_chat(update):
    return CHATS_DICT[update.effective_chat.id]


def save_current_state(update, state):
    if update.effective_chat.id not in CHATS_DICT:
        CHATS_DICT[update.effective_chat.id] = Chat(update.effective_chat.id)
    CHATS_DICT[update.effective_chat.id].user_state = state
    return state


def get_current_state(update):
    if update.effective_chat.id not in CHATS_DICT:
        return None
    return CHATS_DICT[update.effective_chat.id].user_state


def save_message_id(update, message):
    if update.effective_chat.id not in CHATS_DICT:
        CHATS_DICT[update.effective_chat.id] = Chat(update.effective_chat.id)
    CHATS_DICT[update.effective_chat.id].prev_message_id = message.message_id


def save_photo_message(update):
    if update.effective_chat.id not in CHATS_DICT:
        CHATS_DICT[update.effective_chat.id] = Chat(update.effective_chat.id)
    CHATS_DICT[update.effective_chat.id].photo_message = update.effective_message


def send_message(update, context, message_text, reply_markup=None):
    return context.bot.send_message(chat_id=update.effective_chat.id,
                                    text=message_text,
                                    parse_mode=telegram.ParseMode.MARKDOWN,
                                    reply_markup=reply_markup)


def delete_prev_message(update, context):
    if update.effective_chat.id not in CHATS_DICT:
        return
    message_id = CHATS_DICT[update.effective_chat.id].prev_message_id
    try:
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message_id)
    except telegram.error.TelegramError as e:
        _LOGGER.warning(e)


def delete_prev_keyboard(update, context):
    if update.effective_chat.id not in CHATS_DICT:
        return
    message_id = CHATS_DICT[update.effective_chat.id].prev_message_id
    try:
        context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id,
                                              reply_markup=None, message_id=message_id)
    except telegram.error.TelegramError as e:
        _LOGGER.warning(e)


def edit_prev_keyboard(update, context, reply_markup):
    if update.effective_chat.id not in CHATS_DICT:
        return
    message_id = CHATS_DICT[update.effective_chat.id].prev_message_id
    try:
        context.bot.edit_message_reply_markup(chat_id=update.effective_chat.id,
                                              reply_markup=reply_markup, message_id=message_id)
    except telegram.error.TelegramError as e:
        _LOGGER.warning(e)


def post_item_command_handler(update, context):
    message_text = "⬇️⬇️⬇  ⬇️⬇️⬇️"
    keyboard = [[InlineKeyboardButton(CallbackDataEnum.POSTITEM.value, callback_data=CallbackDataEnum.POSTITEM.name)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=message_text,
                                       reply_markup=reply_markup,
                                       parse_mode=telegram.ParseMode.MARKDOWN)

    save_message_id(update, message)


def post_item_handler(update, context, keyboard_only=False):
    message_text = category_message_text()

    keyboard = [
        [InlineKeyboardButton(CategoryEnum.BICYCLE.value, callback_data=CategoryEnum.BICYCLE.name),
         InlineKeyboardButton(CategoryEnum.COMPONENTS.value, callback_data=CategoryEnum.COMPONENTS.name)],

        [InlineKeyboardButton(CategoryEnum.WHEELS.value, callback_data=CategoryEnum.WHEELS.name),
         InlineKeyboardButton(CategoryEnum.SERVICE.value, callback_data=CategoryEnum.SERVICE.name)],

        [InlineKeyboardButton(CategoryEnum.ACCESSORIES.value, callback_data=CategoryEnum.ACCESSORIES.name),
         InlineKeyboardButton(CategoryEnum.BAGS.value, callback_data=CategoryEnum.BAGS.name)],

        [InlineKeyboardButton(CategoryEnum.CLOTHES.value, callback_data=CategoryEnum.CLOTHES.name),
         InlineKeyboardButton(CategoryEnum.SHOES.value, callback_data=CategoryEnum.SHOES.name),
         InlineKeyboardButton(CategoryEnum.HELMETS.value, callback_data=CategoryEnum.HELMETS.name)]]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if not keyboard_only:
        message = context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=message_text, reply_markup=reply_markup,
                                           parse_mode=telegram.ParseMode.MARKDOWN)

        delete_prev_message(update, context)

        save_message_id(update, message)
    else:
        edit_prev_keyboard(update, context, reply_markup)

    return save_current_state(update, UserState.WAITING_FOR_CATEGORY)


def post_item_category(update, context, category):
    if not isinstance(category, CategoryEnum):
        return ConversationHandler.END

    if category == CategoryEnum.BICYCLE:
        return post_item_bicycle_category(update, context)
    if category == CategoryEnum.COMPONENTS:
        return post_item_component_category(update, context)
    if category == CategoryEnum.ACCESSORIES:
        return post_item_show_subcategory(update, context, AccessoriesCategoryEnum, UserState.WAITING_FOR_ACCESSORIES)
    if category == CategoryEnum.WHEELS:
        return post_item_show_subcategory(update, context, WheelsCategoryEnum, UserState.WAITING_FOR_WHEELS)
    if category == CategoryEnum.BAGS:
        return post_item_show_subcategory(update, context, BagsCategoryEnum, UserState.WAITING_FOR_BAGS)
    if category == CategoryEnum.SERVICE:
        return post_item_show_subcategory(update, context, ServiceCategoryEnum, UserState.WAITING_FOR_SERVICE)

    delete_prev_keyboard(update, context)

    if category == CategoryEnum.CLOTHES:
        return post_item_pre_photo(update, context, category)
    if category == CategoryEnum.SHOES:
        return post_item_pre_photo(update, context, category)
    if category == CategoryEnum.HELMETS:
        return post_item_pre_photo(update, context, category)


def post_item_bicycle_category(update, context):
    keyboard = [
        [get_button_for_enum(BicycleCategoryEnum.ROAD), get_button_for_enum(BicycleCategoryEnum.FIX)],
        [get_button_for_enum(BicycleCategoryEnum.CYCLOCROSS), get_button_for_enum(BicycleCategoryEnum.SINGLE)],

        [get_button_for_enum(BicycleCategoryEnum.GRAVEL), get_button_for_enum(BicycleCategoryEnum.TOURING)],

        [get_button_for_enum(CallbackDataEnum.BACK)],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    edit_prev_keyboard(update, context, reply_markup)

    return save_current_state(update, UserState.WAITING_FOR_BICYCLE)


def post_item_component_category(update, context):
    keyboard = [
        [get_button_for_enum(ComponentCategoryEnum.FRAME), get_button_for_enum(ComponentCategoryEnum.FORK)],
        [get_button_for_enum(ComponentCategoryEnum.BRAKES), get_button_for_enum(ComponentCategoryEnum.STEERING)],

        [get_button_for_enum(ComponentCategoryEnum.SEATING),
         get_button_for_enum(ComponentCategoryEnum.TRANSMISSION),
         get_button_for_enum(ComponentCategoryEnum.PEDALS)],

        [get_button_for_enum(CallbackDataEnum.BACK)],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    edit_prev_keyboard(update, context, reply_markup)

    return save_current_state(update, UserState.WAITING_FOR_COMPONENT)


def post_item_show_subcategory(update, context, category_enum, state):
    keyboard = keyboard_for_enum(category_enum)
    keyboard.append([get_button_for_enum(CallbackDataEnum.BACK)])
    reply_markup = InlineKeyboardMarkup(keyboard)
    edit_prev_keyboard(update, context, reply_markup)
    return save_current_state(update, state)


def post_item_go_back(update, context):
    state = CHATS_DICT[update.effective_chat.id].user_state

    new_state = ConversationHandler.END

    if state in (UserState.WAITING_FOR_BICYCLE,
                 UserState.WAITING_FOR_COMPONENT,
                 UserState.WAITING_FOR_WHEELS,
                 UserState.WAITING_FOR_BAGS,
                 UserState.WAITING_FOR_ACCESSORIES,
                 UserState.WAITING_FOR_SERVICE):
        return post_item_handler(update, context, keyboard_only=True)

    if state in (UserState.WAITING_FOR_SEATING,
                 UserState.WAITING_FOR_STEERING,
                 UserState.WAITING_FOR_PEDALS):
        return post_item_component_category(update, context)

    return new_state


def post_item_seating_category(update, context):
    keyboard = [
        [get_button_for_enum(SeatingCategoryEnum.SADDLES),
         get_button_for_enum(SeatingCategoryEnum.SEATPOST),
         get_button_for_enum(SeatingCategoryEnum.ZAZHIM)],

        [get_button_for_enum(CallbackDataEnum.BACK)],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    edit_prev_keyboard(update, context, reply_markup)

    return save_current_state(update, UserState.WAITING_FOR_SEATING)


def post_item_pedals_category(update, context):
    keyboard = [
        [get_button_for_enum(PedalsCategoryEnum.PEDALS), get_button_for_enum(PedalsCategoryEnum.CLEATS)],
        [get_button_for_enum(PedalsCategoryEnum.STRAPS), get_button_for_enum(PedalsCategoryEnum.TOECLIP)],

        [get_button_for_enum(CallbackDataEnum.BACK)],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    edit_prev_keyboard(update, context, reply_markup)

    return save_current_state(update, UserState.WAITING_FOR_PEDALS)


def post_item_steering_category(update, context):
    keyboard = [
        [get_button_for_enum(SteeringCategoryEnum.HANDLEBARS), get_button_for_enum(SteeringCategoryEnum.STEMS)],
        [get_button_for_enum(SteeringCategoryEnum.HEADSETS), get_button_for_enum(SteeringCategoryEnum.TOPCAPS)],

        [get_button_for_enum(SteeringCategoryEnum.SPACERS),
         get_button_for_enum(SteeringCategoryEnum.BARTAPES),
         get_button_for_enum(SteeringCategoryEnum.GRIPS)],

        [get_button_for_enum(CallbackDataEnum.BACK)],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    edit_prev_keyboard(update, context, reply_markup)

    return save_current_state(update, UserState.WAITING_FOR_STEERING)


def post_item_process_subcategory(update, context, category):
    delete_prev_keyboard(update, context)

    if isinstance(category, ComponentCategoryEnum):
        get_chat(update).category_dict[0] = CategoryEnum.COMPONENTS
        get_chat(update).category_dict[1] = category
        if category == ComponentCategoryEnum.SEATING:
            return post_item_seating_category(update, context)
        if category == ComponentCategoryEnum.PEDALS:
            return post_item_pedals_category(update, context)
        if category == ComponentCategoryEnum.STEERING:
            return post_item_steering_category(update, context)

    if isinstance(category, SeatingCategoryEnum):
        get_chat(update).category_dict[0] = CategoryEnum.COMPONENTS
        get_chat(update).category_dict[1] = ComponentCategoryEnum.SEATING
        get_chat(update).category_dict[2] = category
    if isinstance(category, PedalsCategoryEnum):
        get_chat(update).category_dict[0] = CategoryEnum.COMPONENTS
        get_chat(update).category_dict[1] = ComponentCategoryEnum.PEDALS
        get_chat(update).category_dict[2] = category
    if isinstance(category, SteeringCategoryEnum):
        get_chat(update).category_dict[0] = CategoryEnum.COMPONENTS
        get_chat(update).category_dict[1] = ComponentCategoryEnum.STEERING
        get_chat(update).category_dict[2] = category

    message_text = photo_message_text()

    category_string = get_chat(update).get_full_category_string()
    message_text = "*{}*\n{}".format(category_string, message_text)

    message = context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=message_text,
                                       parse_mode=telegram.ParseMode.MARKDOWN)

    save_message_id(update, message)

    return save_current_state(update, UserState.WAITING_FOR_PHOTO)


def post_item_pre_photo(update, context, category):
    get_chat(update).category_dict[0] = category

    message_text = photo_message_text()
    message = context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=message_text, parse_mode=telegram.ParseMode.MARKDOWN)

    save_message_id(update, message)

    return save_current_state(update, UserState.WAITING_FOR_PHOTO)


def post_item_process_photo(update, context):
    keyboard = [
        [InlineKeyboardButton(x.value, callback_data=x.name) for x in CurrencyEnum]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    save_photo_message(update)

    message_text = "Выбери валюту\n"
    message = context.bot.send_message(chat_id=update.effective_chat.id, text=message_text, reply_markup=reply_markup)

    save_message_id(update, message)

    return UserState.WAITING_FOR_CURRENCY


def post_item_process_currency(update, context, currency):
    get_chat(update).currency = currency
    message_text = "Введи цену в выбранной валюте *{}*\n".format(CurrencyEnum[currency.name].value)
    delete_prev_message(update, context)
    message = context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=message_text, parse_mode=telegram.ParseMode.MARKDOWN)

    save_message_id(update, message)

    return UserState.WAITING_FOR_PRICE


def post_item_process_price(update, context):
    price = update.effective_message.text

    if not REGEXP_ONLY_DIGITS.match(price):
        send_message(update, context, "Я приму лишь цифры в цене, давай еще разок...")
        return UserState.WAITING_FOR_PRICE

    get_chat(update).price = int(price)

    message_text = """ Укажи дружишь ли ты с доставкой данного товара"""

    keyboard = [
        [InlineKeyboardButton(x.value, callback_data=x.name) for x in ShippingEnum]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = context.bot.send_message(chat_id=update.effective_chat.id, reply_markup=reply_markup,
                                       text=message_text, parse_mode=telegram.ParseMode.MARKDOWN)

    save_message_id(update, message)

    return UserState.WAITING_FOR_SHIP




def post_item_process_ship(update, context, ship):
    get_chat(update).ship = ship

    message_text = "Ты выбрал такой способ доставки: *{}*".format(ship.value)
    send_message(update, context, message_text)

    message_text = """📍 *Город.*

Выбери город, в котором находится товар. 
Если города нет в списке нажми кнопку *{}*
    """.format(CallbackDataEnum.CITY_OTHER.value)
    delete_prev_keyboard(update, context)

    top_cities = get_top_cities()

    keyboard = []
    counter = 0
    row = []
    for c in top_cities:
        row.append(InlineKeyboardButton(c.title, callback_data=CallbackDataEnum.CITY.name + str(c.id)))
        if counter % 2 == 0:
            keyboard.append(row)
            row = []
        counter += 1

    keyboard.append(
        [InlineKeyboardButton(CallbackDataEnum.CITY_OTHER.value, callback_data=CallbackDataEnum.CITY_OTHER.name)])

    reply_markup = InlineKeyboardMarkup(keyboard)

    message = context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=message_text,
                                       reply_markup=reply_markup,
                                       parse_mode=telegram.ParseMode.MARKDOWN)

    save_message_id(update, message)

    return UserState.WAITING_FOR_CITY


def post_item_process_city(update, context, city):
    get_chat(update).city = city

    message_text = "Ты выбрал город *{}*".format(city.title)
    send_message(update, context, message_text)

    message_text = """⭐️ *Наименование.*

Коротко напиши о товаре (название, бренд, модель, год и тп). 
Например: _стальной фрейм Fuji Declaration 2018._
    """

    delete_prev_keyboard(update, context)

    send_message(update, context, message_text)

    return UserState.WAITING_FOR_CAPTION


def post_item_process_caption(update, context):
    caption = update.effective_message.text

    if caption == '/cancel':
        return ConversationHandler.END

    # if update.effective_user.username:
    #     description = "@" + update.effective_user.username + "\n" + description

    # get photo for this user and send photo+desc to channel
    # ACTIVE_USERS[update.effective_user]["description"] = description

    CHATS_DICT[update.effective_chat.id].caption = caption

    message_text = """➕ *Описание.*

Сейчас более подробно опиши свой товар в произвольной форме. 
Например: _размер 52, состояние хорошее, есть царапины._
"""
    context.bot.send_message(update.effective_chat.id, message_text, parse_mode=telegram.ParseMode.MARKDOWN)

    return UserState.WAITING_FOR_DESCRIPTION


def build_product_text(update):

    if update.effective_user.username:
        seller_name = update.effective_user.username
    else:
        seller_name = update.effective_user.full_name

    seller = '<a href="tg://user?id={id}">{name}</a>'.format(id=update.effective_user.id, name=seller_name)

    chat = get_chat(update)

    category_string = chat.get_full_category_string()
    hashtags = chat.get_hashtags()

    text = "<b>{category_string}</b>\n" \
           "{hashtags}\n\n" \
           "<b>Наименование:</b> {caption}\n\n" \
           "<b>Описание:</b> {descr}\n\n" \
           "<b>Город:</b> {city}\n\n" \
           "<b>Цена:</b> {price} {currency}\n\n" \
           "<b>Продавец:</b> {seller}".format(
            category_string=category_string,
            hashtags=hashtags,
            caption=html.escape(chat.caption),
            descr=html.escape(chat.description),
            city=chat.city.title,
            price=chat.price,
            currency=chat.currency.value,
            seller=seller)

    # text = html.escape(text)

    return text


def post_item_process_description(update, context):
    description = update.effective_message.text

    if description == '/cancel':
        return ConversationHandler.END

    get_chat(update).description = description

    chat = get_chat(update)
    text = build_product_text(update)
    context.bot.send_photo(chat_id=chat.chat_id,
                           photo=chat.photo_message.photo[-1].file_id,
                           caption=text,
                           parse_mode=telegram.ParseMode.HTML)

    keyboard = [
        [InlineKeyboardButton(CallbackDataEnum.DONE.value, callback_data=CallbackDataEnum.DONE.name),
         InlineKeyboardButton(CallbackDataEnum.CANCEL.value, callback_data=CallbackDataEnum.CANCEL.name)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_text = \
        "Нажми *{done}* для постинга на канал @{channel} или *{cancel}* для отмены.".format(
            done=CallbackDataEnum.DONE.value,
            cancel=CallbackDataEnum.CANCEL.value,
            channel=_CHANNEL)
    message = send_message(update, context, message_text, reply_markup)
    save_message_id(update, message)

    return UserState.WAITING_FOR_APPROVE


def post_item_process_approve(update, context):
    delete_prev_keyboard(update, context)

    chat = get_chat(update)
    text = build_product_text(update)
    context.bot.send_photo(chat_id='@' + _CHANNEL,
                           photo=chat.photo_message.photo[-1].file_id,
                           caption=text,
                           parse_mode=telegram.ParseMode.HTML)

    # TODO: add link to post
    message_text = "Товар размещен на канале @{}.\nЕсли захочется повторить жми /postitem".format(_CHANNEL)
    send_message(update, context, message_text)

    return ConversationHandler.END


def cancel_handler(update, context):
    delete_prev_keyboard(update, context)
    send_message(update, context, "Всё, проехали...\nЕсли захочется повторить жми /postitem")
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
    dispatcher.add_handler(CommandHandler('postitem', post_item_command_handler))

    back_handler = CallbackQueryHandler(post_item_go_back, pattern='^' + CallbackDataEnum.BACK.name + '$')

    def do_shit(enum):
        handlers = [
            CallbackQueryHandler(
                partial(post_item_process_subcategory, category=x),
                pattern='^' + x.name + '$') for x in enum]
        handlers.append(back_handler)
        return handlers

    waiting_for_bicycle_h = do_shit(BicycleCategoryEnum)

    waiting_for_component_h = do_shit(ComponentCategoryEnum)
    waiting_for_seating_h = do_shit(SeatingCategoryEnum)
    waiting_for_steering_h = do_shit(SteeringCategoryEnum)
    waiting_for_pedals_h = do_shit(PedalsCategoryEnum)

    waiting_for_accessories_h = do_shit(AccessoriesCategoryEnum)
    waiting_for_bags_h = do_shit(BagsCategoryEnum)
    waiting_for_wheels_h = do_shit(WheelsCategoryEnum)
    waiting_for_service_h = do_shit(ServiceCategoryEnum)

    top_cities = get_top_cities()

    dispatcher.add_handler(
        ConversationHandler(
            entry_points=[
                CallbackQueryHandler(post_item_handler, pattern=('^' + CallbackDataEnum.POSTITEM.name + '$'))],
            states={
                UserState.WAITING_FOR_CATEGORY:
                    [CallbackQueryHandler(partial(post_item_category, category=x),
                                          pattern='^' + x.name + '$') for x in CategoryEnum],

                UserState.WAITING_FOR_BICYCLE: waiting_for_bicycle_h,
                UserState.WAITING_FOR_COMPONENT: waiting_for_component_h,

                UserState.WAITING_FOR_SEATING: waiting_for_seating_h,
                UserState.WAITING_FOR_STEERING: waiting_for_steering_h,
                UserState.WAITING_FOR_PEDALS: waiting_for_pedals_h,

                UserState.WAITING_FOR_WHEELS: waiting_for_wheels_h,
                UserState.WAITING_FOR_ACCESSORIES: waiting_for_accessories_h,
                UserState.WAITING_FOR_BAGS: waiting_for_bags_h,
                UserState.WAITING_FOR_SERVICE: waiting_for_service_h,

                UserState.WAITING_FOR_PHOTO: [MessageHandler(
                    callback=post_item_process_photo, filters=Filters.photo)],

                UserState.WAITING_FOR_CURRENCY:
                    [CallbackQueryHandler(partial(post_item_process_currency, currency=x),
                                          pattern='^' + x.name + '$') for x in CurrencyEnum],

                UserState.WAITING_FOR_PRICE: [MessageHandler(
                    callback=post_item_process_price, filters=Filters.text)],

                UserState.WAITING_FOR_SHIP:
                    [CallbackQueryHandler(partial(post_item_process_ship, ship=x),
                                          pattern='^' + x.name + '$') for x in ShippingEnum],

                UserState.WAITING_FOR_CITY:
                    [CallbackQueryHandler(partial(post_item_process_city, city=x),
                                          pattern='^' + CallbackDataEnum.CITY.name + str(x.id) + '$') for x in
                     top_cities],

                UserState.WAITING_FOR_CAPTION: [MessageHandler(
                    callback=post_item_process_caption, filters=Filters.text)],

                UserState.WAITING_FOR_DESCRIPTION: [MessageHandler(
                    callback=post_item_process_description, filters=Filters.text)],

                UserState.WAITING_FOR_APPROVE:
                    [CallbackQueryHandler(post_item_process_approve, pattern='^' + CallbackDataEnum.DONE.name + '$'),
                     CallbackQueryHandler(cancel_handler, pattern='^' + CallbackDataEnum.CANCEL.name + '$')]
            },
            fallbacks=[CommandHandler('cancel', cancel_handler)],
            per_message=False)
    )

    dispatcher.add_error_handler(error)

    updater.start_polling()
    updater.idle()
