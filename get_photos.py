# coding=utf-8

import json

import barahl0bot
from broadcast import broadcast_message
from check_photo import is_photo_unique
from util import bot_util
import time

_PREVIOUS_PHOTO_DATE_FILENAME = barahl0bot.DATA_DIRNAME + 'previous_photo_date'
_HASH_FILENAME = barahl0bot.DATA_DIRNAME + 'hash'

def write_previous_photo_date(d, a):
    open(_PREVIOUS_PHOTO_DATE_FILENAME + a, 'w').write(str(d))


def read_previous_photo_date(a):
    u = bot_util.read_one_string_file(_PREVIOUS_PHOTO_DATE_FILENAME + a)
    if u == '' or None == u:
        return 0
    return int(u)


def build_url(owner_id, album_id):
    return "https://api.vk.com/method/photos.get?album_id={a}&owner_id={o}&rev=1&v=5.63".format(a=album_id, o=owner_id)


def get_photo_url(latest_photo):
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


def build_message(latest_photo):
    if latest_photo is None:
        return None
    photo_url = get_photo_url(latest_photo)
    user_id = ""
    if 'user_id' in latest_photo:
        user_id = latest_photo['user_id']
        if user_id == 100:
            user_id = None
        else:
            user_id = str(user_id)
    text = ""
    if 'text' in latest_photo:
        text = latest_photo['text']
    photo_id = ""
    if 'id' in latest_photo:
        photo_id = str(latest_photo['id'])

    latest_product = u""
    latest_product += photo_url + "\n\n"
    if text != "":
        text = text.lower()
        text = text.replace('\n', ' ')
        latest_product += u"Описание: " + text + "\n\n"
    if user_id is not None:
        latest_product += u"Продавец: https://vk.com/id" + user_id + "\n"
    latest_product += u"Фото: https://vk.com/photo" + owner_id + "_" + photo_id + "\n"

    return latest_product


def get_latest_for_album(owner_id, album_id):
    u = build_url(owner_id, album_id)
    response_text = bot_util.urlopen(u)
    if not response_text:
        return None
    response_json = json.loads(response_text)
    max_date = read_previous_photo_date(owner_id + "_" + album_id)

    items_to_post = list()
    if 'response' in response_json:
        response = response_json['response']
        if 'items' in response:
            items = response['items']
            last_10_items = items[:10]
            for item in last_10_items:
                if 'date' in item:
                    date = item['date']
                    now_timestamp = bot_util.get_unix_timestamp()
                    diff = now_timestamp - date
                    if diff > 180:
                        items_to_post.append(item)

    return items_to_post
    # photo_url = get_photo_url(latest_item)
    # if photo_url:
    #     if is_photo_unique(_HASH_FILENAME, photo_url):
    #         return build_message(latest_item)
    # return None

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
                goods = get_latest_for_album(owner_id, album_id)
                if goods:
                    for g in goods:
                        photo_url = get_photo_url(g)
                        if photo_url:
                            if is_photo_unique(_HASH_FILENAME, photo_url):
                                message = build_message(g)
                                broadcast_message(message)
        time.sleep(30)
        print "tick"
