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
_TOKEN_VK = barahl0bot.TOKEN_VK
_SECONDS_TO_SLEEP = barahl0bot.SECONDS_TO_SLEEP

_OWNER_ID_POST_BY_GROUP_ADMIN = 100
_LAST_ITEMS_COUNT = 20
_ALBUM_ID_WALL = "wall"
_REGEX_HTTP = re.compile("http")
_REGEX_HTTPS = re.compile("https")

_TIMEOUT_FOR_PHOTO_SECONDS = 180
_TOO_OLD_FOR_PHOTO_SECONDS = 24*60*60

_CHANNELS = barahl0bot.CHANNELS

_VK_SESSION = vk_api.VkApi(token=_TOKEN_VK)
_VK_API = _VK_SESSION.get_api()



def build_album_url(_owner_id, _album_id):
    return "https://vk.com/album{}_{}".format(_owner_id, _album_id)


# def get_url_of_jpeg(latest_photo):
#     if latest_photo is None:
#         return None
#     photo_url = ""
#     if 'photo_1280' in latest_photo:
#         photo_url = latest_photo['photo_1280']
#     elif 'photo_807' in latest_photo:
#         photo_url = latest_photo['photo_807']
#     elif 'photo_604' in latest_photo:
#         photo_url = latest_photo['photo_604']
#     return photo_url


# def get_photo_comments(_owner_id, _photo_id):
#     u = build_photos_get_comments_url(_owner_id, _photo_id, _TOKEN_VK)
#     response_text = bot_util.urlopen(u)
#     if not response_text:
#         return None
#     response_json = json.loads(response_text)
#
#     if 'response' not in response_json:
#         logging.error("no 'response' for getComments")
#         logging.error(response_json)
#         return None
#
#     response = response_json['response']
#     if 'items' not in response:
#         logging.error("no 'items' in 'response' for getComments")
#         logging.error(response)
#         return None
#
#     return response['items']


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


# def get_user_info(_user_id):
#     u = build_users_get_url(_user_id, _TOKEN_VK)
#     response_text = bot_util.urlopen(u)
#     if response_text:
#         response_json = json.loads(response_text)
#         if 'response' in response_json:
#             response = response_json['response']
#             if len(response) == 0:
#                 return None
#             _user_info = response[0]
#             first_name = ""
#             last_name = ""
#             city = ""
#             if "first_name" in _user_info:
#                 first_name = _user_info["first_name"]
#             if "last_name" in _user_info:
#                 last_name = _user_info["last_name"]
#             if "city" in _user_info:
#                 if "title" in _user_info["city"]:
#                     city = _user_info["city"]["title"]
#             _user_info = {'first_name': first_name, 'last_name': last_name, 'city': city}
#             return _user_info
#     return None


def build_message(_good):
    if _good is None:
        return None

    if 'photo' not in _good:
        return None

    photo = _good['photo']
    if photo is None:
        return None

    if 'id' not in photo and 'sizes' not in photo and 'user_id' not in photo:
        return None

    photo_id = str(photo['id'])
    user_id = photo['user_id']
    photo_url = photo['sizes'][-1]['url']

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

    return latest_product


def get_goods_from_album(_owner_id, _album_id):

    response = _VK_API.execute.getPhotosX(album_id=_album_id, owner_id=_owner_id)

    items_to_post = list()

    album_name = response['album_name']
    group_name = response['group_name']
    photos = response['photos']
    comments = response['comments']

    if photos is None:
        logging.error("'photos' is None in response for getPhotosX")
        return None

    for item in photos:
        if 'date' not in item and 'id' not in item:
            logging.error("no 'date' and 'id' in photo!")
            continue
        date = item['date']
        photo_id = item['id']
        now_timestamp = bot_util.get_unix_timestamp()
        diff = now_timestamp - date
        if _TIMEOUT_FOR_PHOTO_SECONDS < diff < _TOO_OLD_FOR_PHOTO_SECONDS:
            photo_url = item['sizes'][-1]['url']
            result = check_photo.is_photo_unique(_HASH_FILENAME, photo_url)
            if result:
                comments_for_photo = [x for x in comments if x['photo_id'] == photo_id][0]['comments']['items']

                time.sleep(1)
                # get user info here
                user_info = _VK_API.users.get(user_ids=item['user_id'], fields='city')[0]

                items_to_post.append({
                    'album_name': album_name,
                    'group_name': group_name,
                    'photo': item,
                    'comments': comments_for_photo,
                    'user': user_info,
                    'hash': result
                })
        else:
            logging.debug("https://vk.com/photo{}_{} too old or too yong ({} seconds of life)".format(_owner_id, photo_id, diff))

    return items_to_post


_LOGS_DIR = 'log'

if __name__ == "__main__":

    if not os.path.exists(_LOGS_DIR):
        os.mkdir(_LOGS_DIR)

    now = datetime.datetime.now()
    now = now.strftime("%d_%m_%Y__%H:%M:%S")
    log_filename = _LOGS_DIR + "/barahl0bot_{}.log".format(now)
    logging.basicConfig(format='%(levelname)s %(asctime)s %(message)s', datefmt='%d/%m/%Y %H:%M:%S ')
    logging.getLogger().setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)s %(asctime)s %(message)s')

    # fh = logging.FileHandler(log_filename)
    # fh.setLevel(logging.DEBUG)
    # fh.setFormatter(formatter)
    # logging.getLogger().addHandler(fh)

    while True:
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

                logging.info("Getting photos from album:")
                logging.info("> https://vk.com/album" + owner_id + "_" + album_id)

                goods = get_goods_from_album(owner_id, album_id)
                if goods:
                    logging.info((len(goods), "new goods"))
                    for g in goods:
                        message = build_message(g)

                        for channel in _CHANNELS:
                            sent = barahl0bot.post_to_channel_html(message, channel)
                            logging.info(sent)
                            if (sent):
                                check_photo.add_photo_hash(_HASH_FILENAME, g['hash'])

                sleep_for_x_seconds = 1
                logging.info("Sleep for {} seconds before next album".format(sleep_for_x_seconds))
                time.sleep(sleep_for_x_seconds)

        logging.info("sleep for {} seconds".format(_SECONDS_TO_SLEEP))
        time.sleep(_SECONDS_TO_SLEEP)
        logging.info("tick")
