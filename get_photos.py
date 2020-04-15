import time
import logging
import datetime
import os
import traceback
import sys
import html

import vk_api.exceptions

import telegram.ext
import telegram.error

from settings import Barahl0botSettings
from database import Barahl0botDatabase
from vkontakte import VkErrorCodesEnum, VkontakteInfoGetter
from structures import Album, Photo, Seller, Product
import util


_OWNER_ID_POST_BY_GROUP_ADMIN = 100
_LAST_ITEMS_COUNT = 20

_LOGGER = logging.getLogger("barahl0bot")
_LOGS_DIR = 'log'
_FH_DEBUG = None
_FH_ERROR = None


def post_to_channel_html(message, channel):
    bot = telegram.Bot(token=_TOKEN_TELEGRAM)
    return bot.send_message('@' + channel, message, parse_mode=telegram.ParseMode.HTML)


def edit_message_channel_html(message_id, message_text, channel):
    bot = telegram.Bot(token=_TOKEN_TELEGRAM)
    try:
        result = bot.edit_message_text(
            chat_id='@' + channel,  message_id=message_id, text=message_text, parse_mode=telegram.ParseMode.HTML
        )
        return result
    except telegram.error.TelegramError as te:
        _LOGGER.warning(te)


def post_to_error_channel(message):
    if not _ERROR_CHANNEL:
        _LOGGER.error("Error channel not set...")
        return

    _LOGGER.debug("Sleep before send error to telegram...")
    time.sleep(3)

    bot = telegram.Bot(token=_TOKEN_TELEGRAM)
    message = "{}\n<code>{}</code>".format(_CHANNEL, html.escape(message))
    return bot.send_message('@' + _ERROR_CHANNEL, message, parse_mode=telegram.ParseMode.HTML)


class TelegramErrorHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        post_to_error_channel(msg)


def try_update_post_message(product, product_from_db):
    seller = product_from_db.seller
    # get seller from db, if not then add it (this code should be above
    if not product_from_db.seller.is_club():
        seller = _VK_INFO_GETTER.get_seller(product_from_db.seller.vk_id)

    product.seller = seller

    same_comments = product.get_comments_text() == product_from_db.comments_text
    same_text = product.get_description_text() == product_from_db.descr

    if same_comments and same_text:
        return

    product.photo_hash = product_from_db.photo_hash
    product.comments_text = product_from_db.comments_text

    message_text = product.build_message_telegram(_CHANNEL)

    # let's not bother telegram...
    _LOGGER.debug("Sleep before telegram message edit")
    time.sleep(3)

    if edit_message_channel_html(message_id=product_from_db.tg_post_id, message_text=message_text, channel=_CHANNEL):
        _LOGGER.info(
            "Edited message https://t.me/{}/{} for photo {}".format(
                _CHANNEL, product_from_db.tg_post_id, product.photo.build_url()))
        _DATABASE.update_product_text_and_comments(product)
        return
    return


def check_for_limit_reached(response):
    if 'execute_errors' in response:
        execute_errors = response['execute_errors']
        limit_reached = False
        for err in execute_errors:
            if err['error_code'] == VkErrorCodesEnum.LIMIT_REACHED:
                limit_reached = True
        return limit_reached


def get_products_from_album(_album):

    response = _VK_INFO_GETTER.get_photos_x(_album)

    if check_for_limit_reached(response):
        _LOGGER.error("Limit reached, sleep for {} seconds".format(_SETTINGS.seconds_to_sleep_limit_reached))
        time.sleep(_SETTINGS.seconds_to_sleep_limit_reached)
        return None

    response = response['response']
    new_products_list = list()

    _album.title = response['album_name']
    _album.group_name = response['group_name']

    photos = response['photos']
    comments = response['comments']

    if photos is None:
        _LOGGER.error("'photos' is None in response for getPhotosX")
        return None

    for vk_photo_dict in photos:

        photo = Photo(vk_photo_dict)
        diff = photo.get_photo_age()

        if diff < _SETTINGS.timeout_for_photo_seconds or diff > _SETTINGS.too_old_for_photo_seconds:
            continue

        comments_for_photo = [x for x in comments if x['photo_id'] == photo.photo_id][0]['comments']['items']

        product = Product(album=_album, photo=photo, comments=comments_for_photo)

        # check photo_id in database, if so try to edit and skip
        product_from_db = _DATABASE.is_photo_posted_by_id(photo)
        if product_from_db:
            try_update_post_message(product, product_from_db)
            continue

        is_duplicate = False
        photo_hash = util.get_photo_hash(photo.get_widest_photo_url())
        prev_by_hash = _DATABASE.is_photo_posted_by_hash(photo_hash)
        prev_tg_post = None
        prev_tg_date = None
        if prev_by_hash:
            prev_tg_post = prev_by_hash['tg_post_id']
            prev_tg_date = prev_by_hash['date']
            is_duplicate = True

        # if user album (id of owner is positive) and 'user_id' not in photo
        if _album.owner_id > 0:
            seller_id = _album.owner_id
        else:
            seller_id = vk_photo_dict['user_id']

        if seller_id != _OWNER_ID_POST_BY_GROUP_ADMIN:
            seller = _DATABASE.is_seller_in_table_by_id(seller_id)
            if not seller:
                time.sleep(2)
                seller = _VK_INFO_GETTER.get_seller(seller_id)
        else:
            seller = Seller()
            seller.vk_id = photo.owner_id

        product.seller = seller
        product.photo_hash = photo_hash
        product.is_duplicate = is_duplicate
        product.prev_tg_date = prev_tg_date
        product.prev_tg_post = prev_tg_post

        new_products_list.append(product)

    return new_products_list


def remove_logger_handlers():
    _LOGGER.removeHandler(_FH_DEBUG)
    _LOGGER.removeHandler(_FH_ERROR)


def set_logger_handlers():
    now = datetime.datetime.now()
    now = now.strftime("%d_%m_%Y")

    log_filename = _LOGS_DIR + "/{}_{}_debug.log".format(_CHANNEL, now)
    fh_debug = logging.FileHandler(log_filename)
    fh_debug.setLevel(logging.DEBUG)
    fh_debug.setFormatter(formatter)
    _LOGGER.addHandler(fh_debug)
    global _FH_DEBUG
    _FH_DEBUG = fh_debug

    log_filename = _LOGS_DIR + "/{}_{}_error.log".format(_CHANNEL, now)
    fh_error = logging.FileHandler(log_filename)
    fh_error.setLevel(logging.ERROR)
    fh_error.setFormatter(formatter)
    _LOGGER.addHandler(fh_error)
    global _FH_ERROR
    _FH_ERROR = fh_error


def post_telegram(_product):
    message = _product.build_message_telegram(_CHANNEL)
    if not message:
        return None
    sent = post_to_channel_html(message, _CHANNEL)
    return sent


def process_album(_album):

    products = None

    try:
        products = get_products_from_album(_album)
    except vk_api.exceptions.ApiHttpError as api_http_error:
        _LOGGER.error("HTTP Error while get products for album {}: {} ".format(api_http_error, _album.build_url()))
        time.sleep(10)

    if not products:
        return

    photos_links = [p.photo.build_url() for p in products]
    _LOGGER.info("{} New products: {}".format(len(products), str(photos_links).strip('[]')))

    now = datetime.datetime.now()
    for p in products:
        # if duplicate but was more than week ago then post
        if p.is_duplicate:
            prev_tg_date = p.prev_tg_date
            if not prev_tg_date:
                _LOGGER.warning("Can't find prev date for product: {}".format(p.photo.build_url()))
                continue
            diff = now - prev_tg_date
            if diff.days < _SETTINGS.days_timeout_for_product:
                _LOGGER.info("Less than {} days for product: {}".
                             format(_SETTINGS.days_timeout_for_product, p.photo.build_url()))
                continue
        sent = post_telegram(p)
        if sent:
            p.tg_post_id = sent['message_id']

            if not p.seller.is_club():
                # check for seller and insert him/her if not in table
                if not _DATABASE.is_seller_in_table_by_id(p.seller.vk_id):
                    _DATABASE.insert_seller(p.seller)
                    _LOGGER.info("New seller saved: {} ".format(p.seller.build_url()))

            # save product to database
            _DATABASE.insert_product(p)

            _LOGGER.info("Posted/saved: https://t.me/{}/{} {} ".format(_CHANNEL, p.tg_post_id, p.photo.build_url()))

        # if too many new goods lets sleep between message send for telegram to be chill
        if len(products) > 3:
            time.sleep(5)


def main_loop():
    previous_day = datetime.datetime.now().day

    while True:

        today = datetime.datetime.now().day
        if today != previous_day:
            remove_logger_handlers()
            set_logger_handlers()

        albums = _DATABASE.get_albums_list()

        for a in albums:
            _LOGGER.info("Processing album: {}".format(a.build_url()))
            process_album(a)
            time.sleep(_SETTINGS.seconds_to_sleep_between_albums)

        previous_day = datetime.datetime.now().day

        _LOGGER.info("Sleep for {} seconds".format(_SETTINGS.seconds_to_sleep))
        time.sleep(_SETTINGS.seconds_to_sleep)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("give me json with settings as argument!")
        exit(-1)

    settings_filename = sys.argv[1]
    _SETTINGS = Barahl0botSettings(settings_filename)

    _TOKEN_TELEGRAM = _SETTINGS.token_telegram
    _CHANNEL = _SETTINGS.channel
    _ERROR_CHANNEL = _SETTINGS.error_channel

    _DATABASE = Barahl0botDatabase(_CHANNEL)

    _VK_INFO_GETTER = VkontakteInfoGetter(_SETTINGS.token_vk)

    try:
        if not os.path.exists(_LOGS_DIR):
            os.mkdir(_LOGS_DIR)

        logging.getLogger().setLevel(logging.ERROR)
        logging.basicConfig(format='%(levelname)s %(asctime)s %(message)s', datefmt='%d/%m/%Y %H:%M:%S ')
        _LOGGER.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(levelname)s %(asctime)s %(message)s')

        set_logger_handlers()
        tg_handler_error = TelegramErrorHandler()
        tg_handler_error.setLevel(logging.ERROR)
        tg_handler_error.setFormatter(formatter)
        _LOGGER.addHandler(tg_handler_error)

        main_loop()

    except Exception as e:
        tb_ex = traceback.extract_tb(e.__traceback__)

        error_message = ""
        for f in tb_ex:
            error_message += " {}:{}\n    {}".format(f.filename, f.lineno, f.line)

        post_to_error_channel(error_message)

        raise
