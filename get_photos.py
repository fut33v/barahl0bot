# coding=utf-8

import json
import re
import time
import logging
import datetime
import os

import vk_api

import barahl0bot
from check_photo import is_photo_unique
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


# def get_post_text(_owner_id, _post_id):
#     if int(_owner_id) < 0:
#         return None
#     _post_id = str(_post_id)
#     full_post_id = _owner_id + "_" + _post_id
#     u = build_wall_get_by_id_url(full_post_id)
#     response_text = bot_util.urlopen(u)
#     if response_text:
#         response_json = json.loads(response_text)
#         if 'response' in response_json:
#             response = response_json['response']
#             if len(response) == 0:
#                 return None
#             if 'text' in response[0]:
#                 return response[0]['text']
#     return None


def build_message(_good):
    if _good is None:
        return None

    _photo_item = _good['item']
    if _photo_item is None:
        return None

    _comments = _good['comments']
    _album_name = _good['album_name']
    _group_name = _good['group_name']

    photo_url = get_url_of_jpeg(_photo_item)

    user_id = ""
    user_first_name = ""
    user_last_name = ""
    user_city = ""
    if 'user_id' in _photo_item:
        user_id = _photo_item['user_id']
        if user_id == _OWNER_ID_POST_BY_GROUP_ADMIN:
            user_id = None
        else:
            user_id = str(user_id)
    if user_id is not None and user_id != "":
        _user_info = get_user_info(user_id)
        if _user_info is not None:
             user_first_name = _user_info['first_name']
             user_last_name = _user_info['last_name']
             user_city = _user_info['city']

    comments = ""
    if _comments and user_id:
        if len(_comments) > 0:
            for c in _comments:
                if 'from_id' and 'text' in c:
                    if int(c['from_id']) == int(user_id) and c['text'] != "":
                        comments += c['text'] + '\n'

    text = ""
    if 'text' in _photo_item:
        text = _photo_item['text']
        if text == '' and user_id:
            if 'post_id' in _photo_item:
                post_id = _photo_item['post_id']
                text = get_post_text(user_id, post_id)
    photo_id = ""
    if 'id' in _photo_item:
        photo_id = str(_photo_item['id'])

    latest_product = ""
    latest_product += "" + photo_url + "\n"
    if _album_name is not None and _group_name is not None:
        latest_product += "<b>" + _group_name + "/" + _album_name + "</b>\n\n"
    if text != "":
        text = text.lower()
        text = text.replace('\n', ' ')
        text = make_numbers_bold(text)
        latest_product += "<b>Описание:</b> " + text + "\n\n"
    if comments != "":
        comments = comments.lower()
        comments = comments.replace('\n', ' ')
        comments = make_numbers_bold(comments)
        latest_product += "<b>Каменты:</b> " + comments + "\n"
    if user_id is not None and user_id != "":
        latest_product += "<b>Продавец:</b> <a href=\"https://vk.com/id" + user_id + "\">" + \
                          user_first_name + " " + user_last_name + "</a>"
    if user_city != "":
        latest_product += " (" + user_city + ")"
    latest_product += "\n"
    nice_photo_url = "https://vk.com/photo" + owner_id + "_" + photo_id
    latest_product += "<b>Фото:</b>" + nice_photo_url + "\n"

    return latest_product


def get_goods_from_album(_owner_id, _album_id):

    response = _VK_API.execute.getPhotosX(album_id=_album_id, owner_id=_owner_id)

    items_to_post = list()

    album_name = response['album_name']
    group_name = response['group_name']
    photos = response['photos']
    comments = response['comments']

    for item in photos:
        if 'date' not in item and 'id' not in item:
            logging.error("no 'date' and 'id' in photo!")
            continue
        date = item['date']
        photo_id = item['id']
        now_timestamp = bot_util.get_unix_timestamp()
        diff = now_timestamp - date
        if _TIMEOUT_FOR_PHOTO_SECONDS < diff < _TOO_OLD_FOR_PHOTO_SECONDS:
            photo_url = item['sizes'][-1]
            if is_photo_unique(_HASH_FILENAME, photo_url):
                items_to_post.append({
                    'album_name': album_name,
                    'group_name': group_name,
                    'item': item,
                })

                # comments = get_photo_comments(_owner_id, photo_id)
                # if int(_owner_id) > 0:
                #     item['user_id'] = _owner_id
                #     user_info = get_user_info(_owner_id)
                #     group_name = str(user_info['first_name']) + " " + str(user_info['last_name'])
                #     if _album_id == _ALBUM_ID_WALL:
                #         album_name = "Фото со стены"

                # items_to_post.append({"item": item,
                #                       'comments': comments,
                #                       'album_name': album_name,
                #                       'group_name': group_name})
        else:
            logging.debug("https://vk.com/photo{}_{} too old or too yong ({} seconds of life)".format(_owner_id, photo_id, diff))

    return items_to_post


# def update_hash(_owner_id, _album_id):
#     response = _VK_API.photos.get(album_id=_album_id, owner_id=_owner_id, extended=1, rev=1, v=5.69)
#     if 'items' not in response:
#         logging.error("no 'items' in response for photos.get")
#         logging.error(response)
#         return None
#     items = response['items']
#     last_10_items = items[:10]
#     for item in last_10_items:
#         photo_url = get_url_of_jpeg(item)
#         is_photo_unique(_HASH_FILENAME, photo_url)


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
                album_line = album_line[:-1]
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
                            sent = barahl0bot.post_to_channel(message, channel)
                            logging.info(sent)

        logging.info("sleep for {} seconds".format(_SECONDS_TO_SLEEP))
        time.sleep(_SECONDS_TO_SLEEP)
        logging.info("tick")
