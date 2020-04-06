import time
import logging
import datetime
import os
import traceback

import vk_api
import telegram.ext
import telegram.error

from settings import Barahl0botSettings
from database import Barahl0botDatabase
from structures import Album, Photo, Seller, Product
import util


_SETTINGS = Barahl0botSettings('settings.json')

_TOKEN_TELEGRAM = _SETTINGS.token_telegram
_CHANNEL = _SETTINGS.channel
_ERROR_CHANNEL = _SETTINGS.error_channel

_SECONDS_TO_SLEEP = _SETTINGS.seconds_to_sleep
_SECONDS_TO_SLEEP_BETWEEN_ALBUMS = 1

_TIMEOUT_FOR_PHOTO_SECONDS = 180
if _SETTINGS.timeout_for_photo_seconds:
    _TIMEOUT_FOR_PHOTO_SECONDS = _SETTINGS.timeout_for_photo_seconds

_TOO_OLD_FOR_PHOTO_SECONDS = 24*60*60
if _SETTINGS.too_old_for_photo_seconds:
    _TOO_OLD_FOR_PHOTO_SECONDS = _SETTINGS.too_old_for_photo_seconds


_OWNER_ID_POST_BY_GROUP_ADMIN = 100
_LAST_ITEMS_COUNT = 20


_DATABASE = Barahl0botDatabase(_CHANNEL)

_VK_SESSION = vk_api.VkApi(token=_SETTINGS.token_vk)
_VK_API = _VK_SESSION.get_api()

_LOGGER = logging.getLogger("barahl0bot")
_LOGS_DIR = 'log'
_FH_DEBUG = None
_FH_ERROR = None


def get_seller_from_vk(_seller_id):
    seller_info = _VK_API.users.get(user_ids=_seller_id, fields='city')[0]
    seller = Seller(seller_info)
    return seller


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
    bot = telegram.Bot(token=_TOKEN_TELEGRAM)
    return bot.send_message('@' + _ERROR_CHANNEL, message, parse_mode=telegram.ParseMode.MARKDOWN)


def get_products_from_album(_album):

    response = _VK_API.execute.getPhotosX(album_id=_album.album_id, owner_id=_album.owner_id)

    new_products_list = list()

    _album.album_name = response['album_name']
    _album.group_name = response['group_name']

    photos = response['photos']
    comments = response['comments']

    if photos is None:
        _LOGGER.error("'photos' is None in response for getPhotosX")
        return None

    for vk_photo_dict in photos:

        photo = Photo(vk_photo_dict)

        now_timestamp = util.get_unix_timestamp()
        diff = now_timestamp - photo.date

        if _TIMEOUT_FOR_PHOTO_SECONDS < diff < _TOO_OLD_FOR_PHOTO_SECONDS:

            comments_for_photo = [x for x in comments if x['photo_id'] == photo.photo_id][0]['comments']['items']

            product = Product(album=_album, photo=photo, comments=comments_for_photo)

            # check photo_id in database
            product_from_db = _DATABASE.is_photo_posted_by_id(photo)
            if product_from_db:
                # _LOGGER.debug("{} has been posted before".format(photo.build_url()))

                seller = product_from_db.seller
                # get seller from db, if not then add it (this code should be above
                if not product_from_db.seller.is_club():
                    seller = get_seller_from_vk(product_from_db.seller.vk_id)

                product.seller = seller

                x1 = product.get_comments_text()
                x2 = product_from_db.comments_text
                same_comments = product.get_comments_text() == product_from_db.comments_text
                same_text = product.get_description_text() == product_from_db.descr

                if same_comments and same_text:
                    continue

                product.photo_hash = product_from_db.photo_hash
                product.comments_text = product_from_db.comments_text

                message_text = product.build_message_telegram(_CHANNEL)
                if edit_message_channel_html(message_id=product_from_db.tg_post_id, message_text=message_text, channel=_CHANNEL):
                    _LOGGER.debug(
                        "Edited message https://t.me/{}/{} for photo {}".format(
                            _CHANNEL, product_from_db.tg_post_id, photo.build_url()))
                continue

            is_duplicate = False
            photo_hash = util.get_photo_hash(photo.get_widest_photo_url())
            prev_by_hash = _DATABASE.is_photo_posted_by_hash(photo_hash)
            prev_tg_post = None
            prev_tg_date = None
            if prev_by_hash:
                # _LOGGER.debug("{} photo with exactly same hash has been posted before".format(photo.build_url()))
                prev_tg_post = prev_by_hash['tg_post_id']
                prev_tg_date = prev_by_hash['date']
                is_duplicate = True

            # if user album (id of owner is positive) and 'user_id' not in photo
            if _album.owner_id > 0:
                seller_id = _album.owner_id
            else:
                seller_id = vk_photo_dict['user_id']

            seller = None
            if seller_id != _OWNER_ID_POST_BY_GROUP_ADMIN:
                time.sleep(1)
                # get user info here
                seller_info = _VK_API.users.get(user_ids=seller_id, fields='city')[0]
                seller = Seller(seller_info)
            else:
                seller = Seller()
                seller.vk_id = photo.owner_id

            product.seller = seller
            product.photo_hash = photo_hash
            product.is_duplicate = is_duplicate
            product.prev_tg_date = prev_tg_date
            product.prev_tg_post = prev_tg_post

            new_products_list.append(product)

        # elif diff < _TIMEOUT_FOR_PHOTO_SECONDS:
        #     _LOGGER.debug("{} too yong ({} seconds of life)".format(photo.build_url(), diff))

    return new_products_list


def remove_logger_handlers():
    _LOGGER.removeHandler(_FH_DEBUG)
    _LOGGER.removeHandler(_FH_ERROR)


def set_logger_handlers():
    now = datetime.datetime.now()
    now = now.strftime("%d_%m_%Y")

    log_filename = _LOGS_DIR + "/{}_debug.log".format(now)
    fh_debug = logging.FileHandler(log_filename)
    fh_debug.setLevel(logging.DEBUG)
    fh_debug.setFormatter(formatter)
    _LOGGER.addHandler(fh_debug)
    global _FH_DEBUG
    _FH_DEBUG = fh_debug

    log_filename = _LOGS_DIR + "/{}_error.log".format(now)
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
    products = get_products_from_album(_album)

    if products:
        _LOGGER.info("{} New goods:".format(len(products)))

        for p in products:
            _LOGGER.info(p.photo.build_url())

        now = datetime.datetime.now()
        for p in products:
            # if duplicate but was more than week ago then post
            if p.is_duplicate:
                prev_tg_date = p.prev_tg_date
                if not prev_tg_date:
                    continue
                diff = now - prev_tg_date
                if diff.days < 7:
                    continue
            sent = post_telegram(p)
            if sent:
                tg_post_id = sent['message_id']
                p.tg_post_id = tg_post_id
                _DATABASE.insert_product(p)

            # if too many new goods lets sleep between message send for
            # telegram to be chill
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
            _LOGGER.info("Getting photos from album: {}".format(a.build_url()))
            process_album(a)
            _LOGGER.info("Sleep for {} seconds before next album".format(_SECONDS_TO_SLEEP_BETWEEN_ALBUMS))
            time.sleep(_SECONDS_TO_SLEEP_BETWEEN_ALBUMS)

        previous_day = datetime.datetime.now().day

        _LOGGER.info("Sleep for {} seconds".format(_SECONDS_TO_SLEEP))
        time.sleep(_SECONDS_TO_SLEEP)
        _LOGGER.info("Tick")


if __name__ == "__main__":

    try:
        if not os.path.exists(_LOGS_DIR):
            os.mkdir(_LOGS_DIR)

        logging.basicConfig(format='%(levelname)s %(asctime)s %(message)s', datefmt='%d/%m/%Y %H:%M:%S ')
        logging.getLogger().setLevel(logging.ERROR)

        _LOGGER.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(levelname)s %(asctime)s %(message)s')

        set_logger_handlers()

        main_loop()

    except Exception as e:
        tb_ex = traceback.extract_tb(e.__traceback__)

        error_message = "```"
        for f in tb_ex:
            error_message += " {}:{}\n    {}".format(f.filename, f.lineno, f.line)
        error_message += "```"

        post_to_error_channel(error_message)

        raise
