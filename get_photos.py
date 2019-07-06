# coding=utf-8

import json
import re
import time

import barahl0bot
from broadcast import broadcast_message
from check_photo import is_photo_unique
from util import bot_util

_HASH_FILENAME = barahl0bot.DATA_DIRNAME + 'hash'
_TOKEN_VK_FILENAME = barahl0bot.DATA_DIRNAME + 'token_vk'
_TOKEN_VK = bot_util.read_one_string_file(_TOKEN_VK_FILENAME)
_OWNER_ID_POST_BY_GROUP_ADMIN = 100
_LAST_ITEMS_COUNT = 20
_ALBUM_ID_WALL = "wall"
_REGEX_HTTP = re.compile("http")
_REGEX_HTTPS = re.compile("https")


def build_photos_get_url(_owner_id, _album_id, _token):
    return "https://api.vk.com/method/photos.get?album_id={a}&owner_id={o}&extended=1&rev=1&v=5.69&access_token={t}".format(a=_album_id,
                                                                                                           o=_owner_id, t=_token)


def build_photos_get_comments_url(_owner_id, _photo_id, _token):
    return "https://api.vk.com/method/photos.getComments?owner_id={o}&photo_id={i}&v=5.69&access_token" \
           "={t}".format(t=_token, o=_owner_id, i=_photo_id)


def build_photos_get_albums_url(_owner_id, _album_id, _token):
    return "https://api.vk.com/method/photos.getAlbums?album_ids={a}&owner_id={o}&v=5.69&access_token={t}". \
        format(a=_album_id, o=_owner_id, t=_token)


def build_groups_get_by_id_url(_group_id, _token):
    return "https://api.vk.com/method/groups.getById?group_id={g}&v=5.63&access_token={t}".format(g=_group_id, t=_token)


def build_users_get_url(_user_id, _token):
    return "https://api.vk.com/method/users.get?user_ids={u}&fields=city&v=5.63&access_token={t}".\
        format(u=_user_id, t=_token)


def build_wall_get_by_id_url(_posts):
    return "https://api.vk.com/method/wall.getById?posts={p}&v=5.69".format(p=_posts)


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
    if not isinstance(_text, unicode):
        return _text
    _tokens = _text.split(u' ')
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
            _tokens_bold.append(u"<b>" + t + u"</b>")
        else:
            _tokens_bold.append(t)

    result = unicode()
    for t in _tokens_bold:
        result += t + " "

    return result


def get_user_info(_user_id):
    u = build_users_get_url(_user_id, _TOKEN_VK)
    response_text = bot_util.urlopen(u)
    if response_text:
        response_json = json.loads(response_text)
        if 'response' in response_json:
            response = response_json['response']
            if len(response) == 0:
                return None
            _user_info = response[0]
            first_name = ""
            last_name = ""
            city = ""
            if "first_name" in _user_info:
                first_name = _user_info["first_name"]
            if "last_name" in _user_info:
                last_name = _user_info["last_name"]
            if "city" in _user_info:
                if "title" in _user_info["city"]:
                    city = _user_info["city"]["title"]
            _user_info = {'first_name': first_name, 'last_name': last_name, 'city': city}
            return _user_info
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
    u = build_groups_get_by_id_url(-_owner_id, _TOKEN_VK)
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


def get_post_text(_owner_id, _post_id):
    if int(_owner_id) < 0:
        return None
    _post_id = str(_post_id)
    full_post_id = _owner_id + "_" + _post_id
    u = build_wall_get_by_id_url(full_post_id)
    response_text = bot_util.urlopen(u)
    if response_text:
        response_json = json.loads(response_text)
        if 'response' in response_json:
            response = response_json['response']
            if len(response) == 0:
                return None
            if 'text' in response[0]:
                return response[0]['text']
    return None


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
        if text == u'' and user_id:
            if 'post_id' in _photo_item:
                post_id = _photo_item['post_id']
                text = get_post_text(user_id, post_id)
    photo_id = ""
    if 'id' in _photo_item:
        photo_id = str(_photo_item['id'])

    latest_product = u""
    latest_product += "" + photo_url + u"\n"
    if _album_name is not None and _group_name is not None:
        latest_product += u"<b>" + _group_name + u"/" + _album_name + u"</b>\n\n"
    if text != "":
        text = text.lower()
        text = text.replace('\n', ' ')
        text = make_numbers_bold(text)
        latest_product += u"<b>Описание:</b> " + text + u"\n\n"
    if comments != "":
        comments = comments.lower()
        comments = comments.replace('\n', ' ')
        comments = make_numbers_bold(comments)
        latest_product += u"<b>Каменты:</b> " + comments + u"\n"
    if user_id is not None and user_id != "":
        latest_product += u"<b>Продавец:</b> <a href=\"https://vk.com/id" + user_id + u"\">" + \
                          user_first_name + u" " + user_last_name + u"</a>"
    if user_city != "":
        latest_product += u" (" + user_city + u")"
    latest_product += "\n"
    nice_photo_url = u"https://vk.com/photo" + owner_id + u"_" + photo_id
    latest_product += u"<b>Фото:</b>" + nice_photo_url + u"\n"

    return latest_product


def get_goods_from_album(_owner_id, _album_id):
    u = build_photos_get_url(_owner_id, _album_id, _TOKEN_VK)
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
            last_items = items[:_LAST_ITEMS_COUNT]

            album_name = get_album_name(_owner_id, _album_id)
            group_name = get_group_name(_owner_id)

            for item in last_items:
                if 'date' in item and 'id' in item:
                    date = item['date']
                    photo_id = item['id']
                    now_timestamp = bot_util.get_unix_timestamp()
                    diff = now_timestamp - date
                    if 180 < diff < 86400:
                        photo_url = get_url_of_jpeg(item)
                        if is_photo_unique(_HASH_FILENAME, photo_url):
                            comments = get_photo_comments(_owner_id, photo_id)
                            if int(_owner_id) > 0:
                                item['user_id'] = _owner_id
                                user_info = get_user_info(_owner_id)
                                group_name = unicode(user_info['first_name']) + u" " + unicode(user_info['last_name'])
                                if _album_id == _ALBUM_ID_WALL:
                                    album_name = u"Фото со стены"
                            items_to_post.append({"item": item,
                                                  'comments': comments,
                                                  'album_name': album_name,
                                                  'group_name': group_name})
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
                if album_id == "00":
                    album_id = "wall"

                print "Getting photos from album:"
                print "> https://vk.com/album" + owner_id + "_" + album_id

                goods = get_goods_from_album(owner_id, album_id)
                if goods:
                    print len(goods), "new goods"
                    for g in goods:
                        message = build_message(g)
                        if not broadcast_message(message):
                            print "failed to send good", g
        time.sleep(30)
        print "tick"
