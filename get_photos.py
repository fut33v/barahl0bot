# coding=utf-8

import json

import barahl0bot
from broadcast import broadcast_message
from check_photo import is_photo_unique
from util import bot_util
import time
import re

_HASH_FILENAME = barahl0bot.DATA_DIRNAME + 'hash'
_TOKEN_VK_FILENAME = barahl0bot.DATA_DIRNAME + 'token_vk'
_TOKEN_VK = bot_util.read_one_string_file(_TOKEN_VK_FILENAME)
RE_DIGITS_BOLD = re.compile("")


def build_photos_get_url(_owner_id, _album_id):
    return "https://api.vk.com/method/photos.get?album_id={a}&owner_id={o}&rev=1&v=5.63".format(a=_album_id,
                                                                                                o=_owner_id)


def build_photos_get_comments_url(_owner_id, _photo_id, _token):
    return "https://api.vk.com/method/photos.getComments?owner_id={o}&photo_id={i}&v=5.63&access_token" \
           "={t}".format(t=_token, o=_owner_id, i=_photo_id)


def build_photos_get_albums_url(_owner_id, _album_id, _token):
    return "https://api.vk.com/method/photos.getAlbums?album_ids={a}&owner_id={o}&v=5.63&access_token={t}". \
        format(a=_album_id, o=_owner_id, t=_token)


def build_groups_get_by_id_url(_group_id):
    return "https://api.vk.com/method/groups.getById?group_id={g}&v=5.63".format(g=_group_id)


def build_users_get_url(_user_id):
    return "https://api.vk.com/method/users.get?user_ids={u}&fields=city&v=5.63".format(u=_user_id)


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


def make_numbers_bold(_text):
    # for i, c in enumerate(_text):
    #     if c.isdigit():
    #         first_part = _text[:i]
    #         last_part = _text[i+1:]
    #         first_part + "<b>{x}</b>".format(x=c) + last_part

    numbers = re.findall('\d+', _text)
    if len(numbers) > 0:
        tmp = _text
        for n in numbers:
            # tmp = re.sub("\D({x})\D".format(x=str(n)), u"<b>{x}</b>".format(x=n), tmp)
            tmp = re.sub("\D({x})\D".format(x=str(n)), u"<b>\g<1></b>", tmp)
        _text = tmp
        print _text
        print numbers
    return _text


def build_message_simple(xyu):
    if xyu is None:
        return None

    photo_dict = xyu[0]
    comments_list = xyu[1]
    album_name = xyu[2]
    group_name = xyu[3]

    if photo_dict is None:
        return None

    photo_url = get_url_of_jpeg(photo_dict)
    user_id = ""
    user_first_name = ""
    user_last_name = ""
    user_city = ""
    if 'user_id' in photo_dict:
        user_id = photo_dict['user_id']
        if user_id == 100:
            user_id = None
        else:
            user_id = str(user_id)

    if user_id is not None:
        u = get_user_info(user_id)
        user_first_name = u[0]
        user_last_name = u[1]
        user_city = u[2]

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
    latest_product += "" + photo_url + u"\n"
    if album_name is not None and group_name is not None:
        latest_product += group_name + u"/" + album_name + u"\n\n"
    if text != "":
        text = text.lower()
        text = text.replace('\n', ' ')
        latest_product += u"Описание: " + text + "\n\n"
    if comments != "":
        comments = comments.lower()
        comments = comments.replace('\n', ' ')
        latest_product += u"Каменты: " + comments + "\n"
    if user_id is not None and user_id != "":
        latest_product += u"Продавец: https://vk.com/id" + user_id + u"\n" + user_first_name + u" " + user_last_name
    if user_city != "":
        latest_product += u" (" + user_city + u")"
    latest_product += "\n"
    latest_product += u"Фото: https://vk.com/photo" + owner_id + u"_" + photo_id + u"\n"

    return latest_product


def build_message(xyu):
    if xyu is None:
        return None

    photo_dict = xyu[0]
    comments_list = xyu[1]
    album_name = xyu[2]
    group_name = xyu[3]

    if photo_dict is None:
        return None

    photo_url = get_url_of_jpeg(photo_dict)
    user_id = ""
    user_first_name = ""
    user_last_name = ""
    user_city = ""
    if 'user_id' in photo_dict:
        user_id = photo_dict['user_id']
        if user_id == 100:
            user_id = None
        else:
            user_id = str(user_id)

    if user_id is not None:
        u = get_user_info(user_id)
        user_first_name = u[0]
        user_last_name = u[1]
        user_city = u[2]

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
    latest_product += "" + photo_url + u"\n"
    if album_name is not None and group_name is not None:
        latest_product += u"<b>" + group_name + u"/" + album_name + u"</b>\n\n"
    if text != "":
        text = text.lower()
        text = text.replace('\n', ' ')
        # text = make_numbers_bold(text)
        latest_product += u"<b>Описание:</b> " + text + u"\n\n"
    if comments != "":
        comments = comments.lower()
        comments = comments.replace('\n', ' ')
        # comments = make_numbers_bold(comments)
        latest_product += u"<b>Каменты:</b> " + comments + u"\n"
    if user_id is not None and user_id != "":
        latest_product += u"<b>Продавец:</b> <a href=\"https://vk.com/id" + user_id + u"\">" + \
                          user_first_name + u" " + user_last_name + u"</a>"
    if user_city != "":
        latest_product += u" (" + user_city + u")"
    latest_product += "\n"
    latest_product += u"<b>Фото:</b> https://vk.com/photo" + owner_id + u"_" + photo_id + u"\n"

    return latest_product


def get_user_info(_user_id):
    u = build_users_get_url(_user_id)
    response_text = bot_util.urlopen(u)
    if response_text:
        response_json = json.loads(response_text)
        if 'response' in response_json:
            response = response_json['response']
            if len(response) == 0:
                return None
            peedor = response[0]
            first_name = ""
            last_name = ""
            city = ""
            if "first_name" in peedor:
                first_name = peedor["first_name"]
            if "last_name" in peedor:
                last_name = peedor["last_name"]
            if "city" in peedor:
                if "title" in peedor["city"]:
                    city = peedor["city"]["title"]
            peedor = (first_name, last_name, city)
            return peedor
    return None


def get_album_name(_owner_id, _album_id):
    u = build_photos_get_albums_url(_owner_id, _album_id, _TOKEN_VK)
    response_text = bot_util.urlopen(u)
    if response_text:
        response_json = json.loads(response_text)
        if 'response' in response_json:
            response = response_json['response']
            if 'items' in response:
                album_info = response['items'][0]
                album_name = album_info['title']
                return album_name
    return None


def get_group_name(_owner_id):
    _owner_id = int(_owner_id)
    if _owner_id > 0:
        return None
    u = build_groups_get_by_id_url(-_owner_id)
    response_text = bot_util.urlopen(u)
    if response_text:
        response_json = json.loads(response_text)
        if 'response' in response_json:
            response = response_json['response']
            if len(response) == 0:
                return None
            if 'name' in response[0]:
                return response[0]['name']
    return None


def get_goods_from_album(_owner_id, _album_id):
    u = build_photos_get_url(_owner_id, _album_id)
    response_text = bot_util.urlopen(u)
    if not response_text:
        print "failed to get data!"
        return None
    response_json = json.loads(response_text)
    items_to_post = list()
    if 'response' in response_json:
        response = response_json['response']
        if 'items' in response:
            items = response['items']
            last_10_items = items[:10]

            album_name = get_album_name(_owner_id, _album_id)
            group_name = get_group_name(_owner_id)
            print "group name : ", group_name
            print "album name : ", album_name

            for item in last_10_items:
                if 'date' in item and 'id' in item:
                    date = item['date']
                    photo_id = item['id']
                    now_timestamp = bot_util.get_unix_timestamp()
                    diff = now_timestamp - date
                    if 180 < diff < 86400:
                        photo_url = get_url_of_jpeg(item)
                        if is_photo_unique(_HASH_FILENAME, photo_url):
                            comments = get_photo_comments(_owner_id, photo_id)
                            items_to_post.append((item, comments, album_name, group_name))
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
                if goods is not None:
                    print len(goods), "new goods"
                    if goods:
                        for g in goods:
                            message = build_message(g)
                            if not broadcast_message(message):
                                print "failed to send good", g
                                message = build_message_simple(g)
                                if not broadcast_message(message):
                                    print "failed to send simple message(", g

        time.sleep(30)
        print "tick"
