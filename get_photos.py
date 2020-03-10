# coding=utf-8

import json
import re
import time
import logging
import datetime
import os

import vk_api

import barahl0bot
import check_photo
from util import bot_util

_HASH_FILENAME = barahl0bot.DATA_DIRNAME + 'hash'
_LAST_FILENAME = barahl0bot.DATA_DIRNAME + 'last'
_TOKEN_VK = barahl0bot.TOKEN_VK
_CHANNELS = barahl0bot.CHANNELS

_SECONDS_TO_SLEEP = barahl0bot.SECONDS_TO_SLEEP
_SECONDS_TO_SLEEP_BETWEEN_ALBUMS = 1
_TIMEOUT_FOR_PHOTO_SECONDS = 180
_TOO_OLD_FOR_PHOTO_SECONDS = 24*60*60
_LAST_FILENAME_RESTRICTION = 500

_OWNER_ID_POST_BY_GROUP_ADMIN = 100
_LAST_ITEMS_COUNT = 20
_ALBUM_ID_WALL = "wall"
_REGEX_HTTP = re.compile("http")
_REGEX_HTTPS = re.compile("https")


_VK_SESSION = vk_api.VkApi(token=_TOKEN_VK)
_VK_API = _VK_SESSION.get_api()

_LOGGER = logging.getLogger("barahl0bot")


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


def build_message(_good):
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
    user_id = photo['user_id']
    photo_url = photo['sizes'][-1]['url']
    photo_date = photo['date']
    photo_time_str = bot_util.get_photo_time_from_unix_timestamp(photo_date)

    group_name = _good['group_name']
    album_name = _good['album_name']
    user_info = _good['user']
    comments = _good['comments']

    first_name = None
    last_name = None
    city = None
    if "first_name" in user_info:
        first_name = user_info["first_name"]
    if "last_name" in user_info:
        last_name = user_info["last_name"]
    if "city" in user_info:
        if "title" in user_info["city"]:
            city = user_info["city"]["title"]

    comments_str = ""
    if comments and user_id:
        if len(comments) > 0:
            for c in comments:
                if 'from_id' and 'text' in c:
                    if int(c['from_id']) == user_id and c['text'] != "":
                        comments_str += c['text'] + '\n'

    if comments_str:
        comments_str = comments_str[:777]

    text = ""
    if 'text' in photo:
        text = photo['text']

    latest_product = ""
    latest_product += "" + photo_url + "\n"
    if album_name is not None and group_name is not None:
        latest_product += "<b>" + group_name + "/" + album_name + "</b>\n\n"
    if text != "":
        text = text.lower()
        text = text.replace('\n', ' ')
        text = make_numbers_bold(text)
        text = text[:777]
        latest_product += "<b>Описание:</b> " + text + "\n\n"
    if comments_str and len(comments_str) + len(text) < 777:
        comments_str = comments_str.lower()
        comments_str = comments_str.replace('\n', ' ')
        comments_str = make_numbers_bold(comments_str)
        latest_product += "<b>Каменты:</b> " + comments_str + "\n\n"
    if user_id is not None and user_id != "":
        latest_product += "<b>Продавец:</b> <a href=\"https://vk.com/id" + str(user_id) + "\">" + \
                          first_name + " " + last_name + "</a>"
    if city:
        latest_product += " (" + city + ")"
    latest_product += "\n"
    nice_photo_url = "https://vk.com/photo" + owner_id + "_" + photo_id
    latest_product += "<b>Фото:</b> " + nice_photo_url + "\n"
    latest_product += photo_time_str + "\n"

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

        photo_id = item['id']
        if check_photo.is_photo_in_last(_LAST_FILENAME, _owner_id, photo_id):
            _LOGGER.debug("https://vk.com/photo{}_{} in last filename".format(_owner_id, photo_id))
            continue

        date = item['date']
        now_timestamp = bot_util.get_unix_timestamp()
        diff = now_timestamp - date

        if _TIMEOUT_FOR_PHOTO_SECONDS < diff < _TOO_OLD_FOR_PHOTO_SECONDS:
            photo_url = item['sizes'][-1]['url']
            photo_hash = check_photo.check_photo_hash(_HASH_FILENAME, photo_url)
            if not photo_hash:
                _LOGGER.debug("{} hash in hash file".format(build_photo_url(_owner_id, photo_id)))
                continue

            comments_for_photo = [x for x in comments if x['photo_id'] == photo_id][0]['comments']['items']

            time.sleep(1)
            # get user info here
            user_info = _VK_API.users.get(user_ids=item['user_id'], fields='city')[0]

            new_goods_list.append({
                'album_name': album_name,
                'group_name': group_name,
                'photo': item,
                'comments': comments_for_photo,
                'user': user_info,
                'hash': photo_hash
            })
        else:
            _LOGGER.debug("{} too old or too yong ({} seconds of life)".format(
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


if __name__ == "__main__":

    if not os.path.exists(_LOGS_DIR):
        os.mkdir(_LOGS_DIR)

    logging.basicConfig(format='%(levelname)s %(asctime)s %(message)s', datefmt='%d/%m/%Y %H:%M:%S ')
    logging.getLogger().setLevel(logging.ERROR)

    _LOGGER.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s %(asctime)s %(message)s')

    set_logger_handlers()

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
                owner_id = oa_id[0]
                album_id = oa_id[1]
                if album_id == "00":
                    album_id = "wall"

                _LOGGER.info("Getting photos from album: {}".format(build_album_url(owner_id, album_id)))

                goods = get_goods_from_album(owner_id, album_id)
                if goods:
                    _LOGGER.info((len(goods), "New goods:"))
                    for g in goods:
                        photo_id = g['photo']['id']
                        _LOGGER.info(build_photo_url(owner_id, photo_id))

                    for g in goods:
                        message = build_message(g)
                        if not message:
                            continue
                        for channel in _CHANNELS:

                            sent = barahl0bot.post_to_channel_html(message, channel)

                            # if we sent message than write hash of photo for future
                            logging.debug(sent)
                            if sent:
                                photo_id = g['photo']['id']
                                check_photo.add_photo_to_last(
                                    _LAST_FILENAME, owner_id, photo_id, _LAST_FILENAME_RESTRICTION
                                )
                                check_photo.add_photo_hash(_HASH_FILENAME, g['hash'])

                            # if too many new goods lets sleep between message send for
                            # telegram to be chill
                            if len(goods) > 3:
                                time.sleep(5)

                _LOGGER.info("Sleep for {} seconds before next album".format(_SECONDS_TO_SLEEP_BETWEEN_ALBUMS))
                time.sleep(_SECONDS_TO_SLEEP_BETWEEN_ALBUMS)

        previous_day = datetime.datetime.now().day

        _LOGGER.info("Sleep for {} seconds".format(_SECONDS_TO_SLEEP))
        time.sleep(_SECONDS_TO_SLEEP)
        _LOGGER.info("Tick")

