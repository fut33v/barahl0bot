# coding=utf-8

import json

import barahl0bot
from broadcast import broadcast_message
from check_photo import is_photo_unique
from util import bot_util
import time

_HASH_FILENAME = barahl0bot.DATA_DIRNAME + 'hash'
_TOKEN_VK_FILENAME = barahl0bot.DATA_DIRNAME + 'token_vk'
_TOKEN_VK = bot_util.read_one_string_file(_TOKEN_VK_FILENAME)


def build_photos_get_url(_owner_id, _album_id):
    return "https://api.vk.com/method/photos.get?album_id={a}&owner_id={o}&rev=1&v=5.63".format(a=_album_id, o=_owner_id)


def build_photos_get_comments_url(_owner_id, _photo_id, token):
    return "https://api.vk.com/method/photos.getComments?owner_id={o}&photo_id={i}&v=5.63&access_token" \
           "={t}".format(t=token, o=_owner_id, i=_photo_id)


def get_url_of_jpeg(latest_photo):
    if latest_photo is None:
        return None
    photo_url = ""
    if 'photo_1280' in latest_photo:
        photo_url = latest_photo['photo_1280']
    elif 'photo_807' in latest_photo:
        photo_url = latest_photo['photo_807']
    elif 'photo_604' in latest_photo:
        photo_url = latest_photo['photo_604']
    return photo_url


def get_photo_comments(_owner_id, _photo_id):
    u = build_photos_get_comments_url(_owner_id, _photo_id, _TOKEN_VK)
    response_text = bot_util.urlopen(u)
    if not response_text:
        return None
    response_json = json.loads(response_text)

    if 'response' in response_json:
        response = response_json['response']
        if 'items' in response:
            return response['items']

    return None


def build_message(xyu):
    if xyu is None:
        return None

    photo_dict = xyu[0]
    comments_list = xyu[1]

    if photo_dict is None:
        return None

    photo_url = get_url_of_jpeg(photo_dict)
    user_id = ""
    if 'user_id' in photo_dict:
        user_id = photo_dict['user_id']
        if user_id == 100:
            user_id = None
        else:
            user_id = str(user_id)

    comments = ""
    if comments_list and user_id:
        if len(comments_list) > 0:
            for c in comments_list:
                if 'from_id' and 'text' in c:
                    if int(c['from_id']) == int(user_id) and c['text'] != "":
                        comments += c['text'] + '\n'

    text = ""
    if 'text' in photo_dict:
        text = photo_dict['text']
    photo_id = ""
    if 'id' in photo_dict:
        photo_id = str(photo_dict['id'])

    latest_product = u""
    latest_product += photo_url + "\n\n"
    if text != "":
        text = text.lower()
        text = text.replace('\n', ' ')
        latest_product += u"Описание: " + text + "\n\n"
    if comments != "":
        latest_product += u"Каменты: " + comments + "\n"
    if user_id is not None and user_id != "":
        latest_product += u"Продавец: https://vk.com/id" + user_id + "\n"
    latest_product += u"Фото: https://vk.com/photo" + owner_id + "_" + photo_id + "\n"

    return latest_product


def get_goods_from_album(owner_id, album_id):
    u = build_photos_get_url(owner_id, album_id)
    response_text = bot_util.urlopen(u)
    if not response_text:
        return None
    response_json = json.loads(response_text)

    items_to_post = list()
    if 'response' in response_json:
        response = response_json['response']
        if 'items' in response:
            items = response['items']
            last_10_items = items[:10]
            for item in last_10_items:
                if 'date' in item and 'id' in item:
                    date = item['date']
                    photo_id = item['id']
                    now_timestamp = bot_util.get_unix_timestamp()
                    diff = now_timestamp - date
                    photo_url = get_url_of_jpeg(item)
                    unique = is_photo_unique(_HASH_FILENAME, photo_url)
                    if unique and diff > 180:
                        comments = get_photo_comments(owner_id, photo_id)
                        items_to_post.append((item, comments))
                        time.sleep(1)

    return items_to_post


def update_hash(_owner_id, _album_id):
    u = build_photos_get_url(_owner_id, _album_id)
    response_text = bot_util.urlopen(u)
    if not response_text:
        return None
    response_json = json.loads(response_text)
    if 'response' in response_json:
        response = response_json['response']
        if 'items' in response:
            items = response['items']
            last_10_items = items[:10]
            for item in last_10_items:
                photo_url = get_url_of_jpeg(item)
                is_photo_unique(_HASH_FILENAME, photo_url)
if __name__ == "__main__":
    while True:
        with open(barahl0bot.ALBUMS_FILENAME, "r") as albums_file:
            lines = albums_file.readlines()
            for l in lines:
                l = l[:-1]
                oa_id = l.split('_')
                if len(oa_id) < 2:
                    continue
                owner_id = oa_id[0]
                album_id = oa_id[1]
                print owner_id, album_id
                goods = get_goods_from_album(owner_id, album_id)
                if goods:
                    for g in goods:
                        message = build_message(g)
                        broadcast_message(message)
        time.sleep(30)
        print "tick"
