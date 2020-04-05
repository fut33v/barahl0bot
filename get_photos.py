import re
import time
import logging
import datetime
import os
import traceback
import html
import hashlib

import pymysql
import vk_api
import telegram.ext

from settings import Barahl0botSettings
from util import bot_util


_CONNECTION = pymysql.connect(host='localhost', user='fut33v', password='', db='barahlochannel', charset='utf8mb4')

_SETTINGS = Barahl0botSettings('settings.json')

_TOKEN_TELEGRAM = _SETTINGS.token_telegram
_TOKEN_VK = _SETTINGS.token_vk
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

_COMMENTS_STRING_RESTRICTION = 600
_DESCRIPTION_STRING_RESTRICTION = 600
_DESCRIPTION_PLUS_COMMENTS_STRING_RESTRICTION = 700

_OWNER_ID_POST_BY_GROUP_ADMIN = 100
_LAST_ITEMS_COUNT = 20
_REGEX_HTTP = re.compile("http")
_REGEX_HTTPS = re.compile("https")


_VK_SESSION = vk_api.VkApi(token=_TOKEN_VK)
_VK_API = _VK_SESSION.get_api()

_LOGGER = logging.getLogger("barahl0bot")
_LOGS_DIR = 'log'
_FH_DEBUG = None
_FH_ERROR = None


class Album:
    _ALBUM_ID_WALL = "wall"

    def __init__(self, _owner_id, _album_id):
        self.owner_id = _owner_id
        self.album_id = _album_id

        self.group_name = None
        self.album_name = None

    def build_url(self):
        return "https://vk.com/album{}_{}".format(self.owner_id, self.album_id)


class Seller:
    def __init__(self, _users_get_result):
        self.vk_id = None
        self.first_name = None
        self.last_name = None
        self.city = None

        if "id" in _users_get_result:
            self.vk_id = _users_get_result["id"]
        if "first_name" in _users_get_result:
            self.first_name = _users_get_result["first_name"]
        if "last_name" in _users_get_result:
            self.last_name = _users_get_result["last_name"]
        if "city" in _users_get_result:
            if "title" in _users_get_result["city"]:
                self.city = _users_get_result["city"]["title"]


class Product:
    def __init__(self, _album, _photo, _comments, _seller, _photo_hash):
        self.album = _album
        self.photo = _photo
        self.comments = _comments
        self.seller = _seller
        self.photo_hash = _photo_hash

        self.is_duplicate = False
        self.prev_tg_post = None
        self.prev_tg_date = None

    def get_comments_text(self, _restrict=True):
        seller_id = self.seller.vk_id
        comments = self.comments

        comments_str = ""
        if comments and seller_id:
            if len(comments) > 0:
                for c in comments:
                    if 'from_id' and 'text' in c:
                        if int(c['from_id']) == seller_id and c['text'] != "":
                            comments_str += c['text'] + '\n'
        if comments_str:
            if _restrict:
                comments_str = comments_str[:_COMMENTS_STRING_RESTRICTION]
            comments_str = comments_str.lower()
            comments_str = comments_str.replace('\n', ' ')
            comments_str = html.escape(comments_str)
            comments_str = make_numbers_bold(comments_str)

        return comments_str

    def get_description_text(self, _restrict=True):
        text = self.photo.text
        text = text.lower()
        text = text.replace('\n', ' ')
        if _restrict:
            text = text[:_DESCRIPTION_STRING_RESTRICTION]
        text = html.escape(text)
        text = make_numbers_bold(text)

        return text

    def build_message_telegram(self):
        photo = self.photo
        photo_url = photo.get_widest_photo_url()

        owner_id = self.album.owner_id
        # seller_id = self.seller.vk_id
        group_name = self.album.group_name
        album_name = self.album.album_name
        seller = self.seller

        latest_product = "" + photo_url + "\n"

        if owner_id > 0:
            latest_product += "<b>{} {}/{}</b>\n\n".format(seller.first_name, seller.last_name, album_name)
        elif album_name and group_name:
            latest_product += "<b>{}/{}</b>\n\n".format(group_name, album_name)

        text = self.get_description_text()
        if text:
            latest_product += "<b>Описание:</b> " + text + "\n\n"

        comments_str = self.get_comments_text()
        if comments_str and len(comments_str) + len(text) < _DESCRIPTION_PLUS_COMMENTS_STRING_RESTRICTION:
            latest_product += "<b>Каменты:</b> " + comments_str + "\n\n"

        # _OWNER_ID_POST_BY_GROUP_ADMIN
        if not self.seller:
            latest_product += \
                "<b>Продавец:</b> <a href=\"https://vk.com/club{}\">{}</a>".format(
                    -owner_id, group_name)
        else:
            latest_product += \
                "<b>Продавец:</b> <a href=\"https://vk.com/id{}\">{} {}</a>".format(
                    seller.vk_id, seller.first_name, seller.last_name)

        if seller.city:
            latest_product += " ({})".format(seller.city)

        latest_product += "\n"

        latest_product += "<b>Фото:</b> {}\n".format(photo.build_url())

        if self.is_duplicate and self.prev_tg_post:
            latest_product += "<b>Предыдущее объявление:</b> <a href=\"https://t.me/{}/{}\">Telegram</a> | barahloch".\
                format(_CHANNEL, self.prev_tg_post)

        return latest_product


class Photo:
    def __init__(self, _photos_get_result):
        self.photo_id = None
        self.owner_id = None
        self.user_id = None
        self.text = None
        self.date = None
        self.sizes = None

        if 'id' not in _photos_get_result or \
                'owner_id' not in _photos_get_result or \
                'text' not in _photos_get_result or \
                'date' not in _photos_get_result or \
                'sizes' not in _photos_get_result:
            _LOGGER.error("Not found one of keys in photo dict")
            return

        self.photo_id = _photos_get_result['id']
        self.owner_id = _photos_get_result['owner_id']
        self.text = _photos_get_result['text']
        self.date = _photos_get_result['date']
        self.sizes = _photos_get_result['sizes']

        if 'user_id' not in _photos_get_result and self.owner_id > 0:
            self.user_id = self.owner_id
        else:
            self.user_id = _photos_get_result['user_id']

    def build_url(self):
        return "https://vk.com/photo{}_{}".format(self.owner_id, self.photo_id)

    def get_widest_photo_url(self):
        photo_url = None
        max_width = 0
        for photo_size in self.sizes:
            width = photo_size['width']
            if width > max_width:
                photo_url = photo_size['url']
                max_width = width
        return photo_url


def post_to_channel_html(message, channel):
    bot = telegram.Bot(token=_TOKEN_TELEGRAM)
    return bot.send_message('@' + channel, message, parse_mode=telegram.ParseMode.HTML)


def post_to_error_channel(message):
    if not _ERROR_CHANNEL:
        _LOGGER.error("Error channel not set...")
        return
    bot = telegram.Bot(token=_TOKEN_TELEGRAM)
    return bot.send_message('@' + _ERROR_CHANNEL, message, parse_mode=telegram.ParseMode.MARKDOWN)


def get_photo_hash(url):
    photo = bot_util.urlopen(url)
    if not photo:
        return None
    sha = hashlib.sha256()
    sha.update(photo)
    h = sha.hexdigest()
    return h


def is_photo_posted_by_id(_owner_id, _photo_id):
    photo_id_str = str(_owner_id) + "_" + str(_photo_id)

    with _CONNECTION.cursor() as cursor:
        # Read a single record
        sql = "SELECT * FROM `goods` WHERE `vk_photo_id`=%s and tg_channel=%s"
        cursor.execute(sql, (photo_id_str, _CHANNEL))
        result = cursor.fetchone()
        if result:
            print("found by id:", result)
            return True

    return False


def get_albums_list():
    with _CONNECTION.cursor() as cursor:
        sql = "SELECT * FROM `albums`"
        cursor.execute(sql)
        result = cursor.fetchall()
        if result:
            albums = []
            for a in result:
                owner_id = a[0]
                album_id = a[1]
                albums.append(Album(owner_id, album_id))
            return albums
    return False


def is_photo_posted_by_hash(_hash):
    with _CONNECTION.cursor() as cursor:
        sql = "SELECT `tg_post_id`,`date` FROM `goods` WHERE `hash`=%s and tg_channel=%s ORDER BY date DESC"
        cursor.execute(sql, (_hash, _CHANNEL))
        result = cursor.fetchone()
        if result:
            return {
                'date': result[1],
                'tg_post_id': result[0]
            }
    return False


def save_good_to_db(_product):
    if not _product.seller:
        _LOGGER.warning("Trying to add good without seller")
        return

    photo = _product.photo
    owner_id = str(_product.album.owner_id)
    photo_id = str(photo.photo_id)
    vk_photo_id = owner_id + "_" + photo_id
    seller_id = int(_product.seller.vk_id)
    tg_post_id = int(_product.tg_post_id)
    photo_link = photo.get_widest_photo_url()
    photo_hash = _product.photo_hash

    descr = ""
    descr += _product.get_description_text()
    descr += _product.get_comments_text()

    with _CONNECTION.cursor() as cursor:
        sql = 'INSERT INTO `goods` VALUES(%s, %s, %s, %s, %s, NOW(), %s, %s);'
        cursor.execute(sql, (vk_photo_id, photo_link, seller_id, descr, tg_post_id, photo_hash, _CHANNEL))

    _CONNECTION.commit()


# def build_photo_url(_owner_id, _photo_id):
#     return "https://vk.com/photo{}_{}".format(_owner_id, _photo_id)


def make_numbers_bold(_text):
    if not isinstance(_text, str):
        return _text
    _tokens = _text.split(' ')
    _tokens_bold = []
    for t in _tokens:
        is_digit = False
        # is_link = False
        for c in t:
            if c.isdigit():
                is_digit = True
        h1 = _REGEX_HTTP.findall(t)
        h2 = _REGEX_HTTPS.findall(t)
        if len(h1) > 0 or len(h2) > 0:
            # is_link = True
            is_digit = False
        if is_digit:
            _tokens_bold.append("<b>" + t + "</b>")
        else:
            _tokens_bold.append(t)

    result = str()
    for t in _tokens_bold:
        result += t + " "

    return result


def get_goods_from_album(_album):

    response = _VK_API.execute.getPhotosX(album_id=_album.album_id, owner_id=_album.owner_id)

    new_goods_list = list()

    _album.album_name = response['album_name']
    _album.group_name = response['group_name']
    photos = response['photos']
    comments = response['comments']

    if photos is None:
        _LOGGER.error("'photos' is None in response for getPhotosX")
        return None

    for vk_photo_dict in photos:
        if 'date' not in vk_photo_dict and 'id' not in vk_photo_dict:
            _LOGGER.error("no 'date' and 'id' in photo!")
            continue

        photo = Photo(vk_photo_dict)

        # date = vk_photo_dict['date']
        # photo_id = vk_photo_dict['id']
        now_timestamp = bot_util.get_unix_timestamp()
        diff = now_timestamp - photo.date

        if _TIMEOUT_FOR_PHOTO_SECONDS < diff < _TOO_OLD_FOR_PHOTO_SECONDS:
            # check photo_id in database
            if is_photo_posted_by_id(_album.owner_id, photo.photo_id):
                _LOGGER.debug("{} has been posted before".format(photo.build_url()))
                continue

            is_duplicate = False
            photo_hash = get_photo_hash(photo.get_widest_photo_url())
            prev_by_hash = is_photo_posted_by_hash(photo_hash)
            prev_tg_post = None
            prev_tg_date = None
            if prev_by_hash:
                _LOGGER.debug("{} photo with exactly same hash has been posted before".format(photo.build_url()))
                prev_tg_post = prev_by_hash['tg_post_id']
                prev_tg_date = prev_by_hash['date']
                is_duplicate = True

            comments_for_photo = [x for x in comments if x['photo_id'] == photo.photo_id][0]['comments']['items']

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

            product = Product(
                _album=_album,
                _photo=photo,
                _comments=comments_for_photo,
                _seller=seller,
                _photo_hash=photo_hash,
            )
            product.is_duplicate = is_duplicate
            product.prev_tg_date = prev_tg_date
            product.prev_tg_post = prev_tg_post

            new_goods_list.append(product)

        elif diff < _TIMEOUT_FOR_PHOTO_SECONDS:
            _LOGGER.debug("{} too yong ({} seconds of life)".format(photo.build_url(), diff))

    return new_goods_list


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
    message = _product.build_message_telegram()
    if not message:
        return None
    sent = post_to_channel_html(message, _CHANNEL)
    return sent


def process_album(_album):
    products = get_goods_from_album(_album)

    if products:
        _LOGGER.info("{} New goods:", len(products))

        for p in products:
            _LOGGER.info(p.photo.build_url())

        now = datetime.datetime.now()
        for p in products:
            # if duplicate but was more than week ago then post
            if p.is_duplicate:
                prev_tg_date = g.prev_tg_date
                if not prev_tg_date:
                    continue
                diff = now - prev_tg_date
                if diff.days < 7:
                    continue
            sent = post_telegram(p)
            if sent:
                tg_post_id = sent['message_id']
                p.tg_post_id = tg_post_id
                save_good_to_db(p)

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

        albums = get_albums_list()
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

    # try:
    if not os.path.exists(_LOGS_DIR):
        os.mkdir(_LOGS_DIR)

    logging.basicConfig(format='%(levelname)s %(asctime)s %(message)s', datefmt='%d/%m/%Y %H:%M:%S ')
    logging.getLogger().setLevel(logging.ERROR)

    _LOGGER.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s %(asctime)s %(message)s')

    set_logger_handlers()

    main_loop()

    # except Exception as e:
    #     tb_ex = traceback.extract_tb(e.__traceback__)
    #
    #     error_message = "```"
    #     for f in tb_ex:
    #         error_message += " {}:{}\n    {}".format(f.filename, f.lineno, f.line)
    #     error_message += "```"
    #
    #     post_to_error_channel(error_message)
    #
    #     raise
