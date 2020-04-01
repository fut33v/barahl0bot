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

import barahl0bot
from util import bot_util


_CONNECTION = pymysql.connect(host='localhost', user='fut33v', password='', db='barahlochannel', charset='utf8mb4')


_HASH_FILENAME = barahl0bot.DATA_DIRNAME + 'hash'
_LAST_FILENAME = barahl0bot.DATA_DIRNAME + 'last'
_TOKEN_VK = barahl0bot.TOKEN_VK
_TOKEN_VK_WALL = barahl0bot.TOKEN_VK_WALL
_CHANNELS = barahl0bot.CHANNELS

_SECONDS_TO_SLEEP = barahl0bot.SECONDS_TO_SLEEP
_SECONDS_TO_SLEEP_BETWEEN_ALBUMS = 1
_TIMEOUT_FOR_PHOTO_SECONDS = 180
_TOO_OLD_FOR_PHOTO_SECONDS = 24*60*60
_LAST_FILENAME_RESTRICTION = 500

_COMMENTS_STRING_RESTRICTION = 600
_DESCRIPTION_STRING_RESTRICTION = 600
_DESCRIPTION_PLUS_COMMENTS_STRING_RESTRICTION = 700

_OWNER_ID_POST_BY_GROUP_ADMIN = 100
_LAST_ITEMS_COUNT = 20
_ALBUM_ID_WALL = "wall"
_REGEX_HTTP = re.compile("http")
_REGEX_HTTPS = re.compile("https")


_VK_SESSION = vk_api.VkApi(token=_TOKEN_VK)
_VK_API = _VK_SESSION.get_api()

_VK_SESSION_WALL = vk_api.VkApi(token=_TOKEN_VK_WALL)
_VK_API_WALL = _VK_SESSION_WALL.get_api()

_LOGGER = logging.getLogger("barahl0bot")


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
        sql = "SELECT * FROM `goods` WHERE `vk_photo_id`=%s"
        cursor.execute(sql, (photo_id_str,))
        result = cursor.fetchone()
        print(result)
        if result:
            return True

    return False


def is_photo_posted_by_hash(_hash):
    with _CONNECTION.cursor() as cursor:
        # Read a single record
        sql = "SELECT `tg_post_id`,`date` FROM `goods` WHERE `hash`=%s ORDER BY date DESC"
        cursor.execute(sql, (_hash,))
        result = cursor.fetchone()
        if result:
            return {
                'date': result[1],
                'tg_post_id': result[0]
            }
    return False


def save_good_to_db(_good):
    photo = _good['photo']
    owner_id = str(_good['owner_id'])
    photo_id = str(photo['id'])
    vk_photo_id = owner_id + "_" + photo_id
    seller_id = int(_good['seller_id'])
    tg_post_id = int(_good['tg_post_id'])
    photo_link = get_widest_photo_url(photo['sizes'])
    photo_hash = _good['hash']

    # photo_date = photo['date']
    # photo_time_str = bot_util.get_photo_time_from_unix_timestamp(photo_date)
    descr = ""
    descr += get_good_description_text(_good)
    descr += get_good_comments_text(_good)

    with _CONNECTION.cursor() as cursor:
        sql = 'INSERT INTO `goods` VALUES(%s, %s, %s, %s, %s, NOW(), %s);'
        cursor.execute(sql, (vk_photo_id, photo_link, seller_id, descr, tg_post_id, photo_hash))

    _CONNECTION.commit()


def get_good_description_text(_good, _restrict=True):
    photo = _good['photo']
    text = ""
    if 'text' in photo:
        text = photo['text']
    if text:
        text = text.lower()
        text = text.replace('\n', ' ')
        if _restrict:
            text = text[:_DESCRIPTION_STRING_RESTRICTION]
        text = html.escape(text)
        text = make_numbers_bold(text)

    return text


def get_good_comments_text(_good, _restrict=True):
    seller_id = _good['seller_id']
    comments = _good['comments']

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


def build_album_url(_owner_id, _album_id):
    return "https://vk.com/album{}_{}".format(_owner_id, _album_id)


def build_photo_url(_owner_id, _photo_id):
    return "https://vk.com/photo{}_{}".format(_owner_id, _photo_id)


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


def get_widest_photo_url(_sizes):
    photo_url = _sizes[-1]['url']
    photo_url = None
    max_width = 0
    for photo_size in _sizes:
        width = photo_size['width']
        if width > max_width:
            photo_url = photo_size['url']
            max_width = width
    return photo_url


def build_message_telegram(_good):
    if _good is None:
        return None

    if 'photo' not in _good:
        return None

    photo = _good['photo']
    if photo is None:
        return None

    if 'id' not in photo and 'sizes' not in photo and 'user_id' not in photo and 'date' not in photo:
        _LOGGER.error("Not found one of keys in photo dict")
        return None

    photo_id = str(photo['id'])

    photo_url = get_widest_photo_url(photo['sizes'])

    owner_id = _good['owner_id']
    seller_id = _good['seller_id']
    seller_info = _good['seller_info']
    group_name = _good['group_name']
    album_name = _good['album_name']

    first_name = ""
    last_name = ""
    city = ""

    if seller_info:
        if "first_name" in seller_info:
            first_name = seller_info["first_name"]
        if "last_name" in seller_info:
            last_name = seller_info["last_name"]
        if "city" in seller_info:
            if "title" in seller_info["city"]:
                city = seller_info["city"]["title"]

    latest_product = "" + photo_url + "\n"

    if owner_id > 0:
        latest_product += "<b>{} {}/{}</b>\n\n".format(first_name, last_name, album_name)
    elif album_name and group_name:
        latest_product += "<b>{}/{}</b>\n\n".format(group_name, album_name)

    text = get_good_description_text(_good)
    if text:
        latest_product += "<b>Описание:</b> " + text + "\n\n"

    comments_str = get_good_comments_text(_good)
    if comments_str and len(comments_str) + len(text) < _DESCRIPTION_PLUS_COMMENTS_STRING_RESTRICTION:
        latest_product += "<b>Каменты:</b> " + comments_str + "\n\n"

    if seller_id:
        if seller_id == _OWNER_ID_POST_BY_GROUP_ADMIN:
            latest_product += \
                "<b>Продавец:</b> <a href=\"https://vk.com/club{}\">{}</a>".format(-owner_id, group_name)
        else:
            latest_product += \
                "<b>Продавец:</b> <a href=\"https://vk.com/id{}\">{} {}</a>".format(seller_id, first_name, last_name)
    if city:
        latest_product += " ({})".format(city)

    latest_product += "\n"

    nice_photo_url = build_photo_url(owner_id, photo_id)
    latest_product += "<b>Фото:</b> {}\n".format(nice_photo_url)

    if _good['duplicate'] and _good['prev_tg_post']:
        latest_product += "<b>Предыдущее объявление:</b> https://t.me/barahlochannel/{}".format(_good['prev_tg_post'])

    return latest_product


def get_goods_from_album(_owner_id, _album_id):

    response = _VK_API.execute.getPhotosX(album_id=_album_id, owner_id=_owner_id)

    new_goods_list = list()

    album_name = response['album_name']
    group_name = response['group_name']
    photos = response['photos']
    comments = response['comments']

    if photos is None:
        _LOGGER.error("'photos' is None in response for getPhotosX")
        return None

    for item in photos:
        if 'date' not in item and 'id' not in item:
            _LOGGER.error("no 'date' and 'id' in photo!")
            continue

        date = item['date']
        now_timestamp = bot_util.get_unix_timestamp()
        diff = now_timestamp - date
        photo_id = item['id']

        if _TIMEOUT_FOR_PHOTO_SECONDS < diff < _TOO_OLD_FOR_PHOTO_SECONDS:
            # check photo_id in database
            if is_photo_posted_by_id(_owner_id, photo_id):
                _LOGGER.debug("{} has been posted before".
                              format(build_photo_url(_owner_id, photo_id)))
                continue

            is_duplicate = False
            photo_hash = get_photo_hash(get_widest_photo_url(item['sizes']))
            prev_by_hash = is_photo_posted_by_hash(photo_hash)
            prev_tg_post = None
            prev_tg_date = None
            if prev_by_hash:
                _LOGGER.debug("{} photo with exactly same hash has been posted before".
                              format(build_photo_url(_owner_id, photo_id)))
                prev_tg_post = prev_by_hash['tg_post_id']
                prev_tg_date = prev_by_hash['date']
                is_duplicate = True

            comments_for_photo = [x for x in comments if x['photo_id'] == photo_id][0]['comments']['items']

            # if user album (id of owner is positive) and 'user_id' not in photo
            if _owner_id > 0:
                seller_id = _owner_id
            else:
                seller_id = item['user_id']

            seller_info = None

            if seller_id != _OWNER_ID_POST_BY_GROUP_ADMIN:
                time.sleep(1)
                # get user info here
                seller_info = _VK_API.users.get(user_ids=seller_id, fields='city')[0]

            new_goods_list.append({
                'photo': item,
                'owner_id': _owner_id,

                'seller_id': seller_id,
                'seller_info': seller_info,

                'album_name': album_name,
                'group_name': group_name,

                'comments': comments_for_photo,

                'hash': photo_hash,
                'duplicate': is_duplicate,
                'prev_tg_post': prev_tg_post,
                'prev_tg_date': prev_tg_date
            })

        elif diff < _TIMEOUT_FOR_PHOTO_SECONDS:
            _LOGGER.debug("{} too yong ({} seconds of life)".format(
                build_photo_url(_owner_id, photo_id), diff)
            )

    return new_goods_list


_LOGS_DIR = 'log'
_FH_DEBUG = None
_FH_ERROR = None


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


def post_telegram(_good):

    message = build_message_telegram(_good)
    owner_id = _good['owner_id']

    if not message:
        return None

    for channel in _CHANNELS:
        sent = barahl0bot.post_to_channel_html(message, channel)
        # if we sent message than write hash of photo for future
        logging.debug(sent)
        return sent


def process_album(_owner_id, _album_id):

    goods = get_goods_from_album(_owner_id, _album_id)

    if goods:
        _LOGGER.info((len(goods), "New goods:"))

        for g in goods:
            photo_id = g['photo']['id']
            _LOGGER.info(build_photo_url(_owner_id, photo_id))

        now = datetime.datetime.now()
        for g in goods:
            # if duplicate but was more than week ago then post
            if g['duplicate']:
                prev_tg_date = g['prev_tg_date']
                if not prev_tg_date:
                    continue
                diff = now - prev_tg_date
                if diff.days < 7:
                    continue
            sent = post_telegram(g)
            if sent:
                tg_post_id = sent['message_id']
                g['tg_post_id'] = tg_post_id

                save_good_to_db(g)

            # if too many new goods lets sleep between message send for
            # telegram to be chill
            if len(goods) > 3:
                time.sleep(5)


def main_loop():
    previous_day = datetime.datetime.now().day

    while True:

        today = datetime.datetime.now().day
        if today != previous_day:
            remove_logger_handlers()
            set_logger_handlers()

        with open(barahl0bot.ALBUMS_FILENAME, "r") as albums_file:
            lines = albums_file.readlines()
            for album_line in lines:
                album_line = album_line.rstrip()
                oa_id = album_line.split('_')
                if len(oa_id) < 2:
                    continue
                owner_id = int(oa_id[0])
                album_id = oa_id[1]
                if album_id == "00":
                    album_id = "wall"

                _LOGGER.info("Getting photos from album: {}".format(build_album_url(owner_id, album_id)))

                process_album(owner_id, album_id)

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

        barahl0bot.post_to_error_channel(error_message)

        raise
