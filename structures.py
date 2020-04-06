import logging
import settings
import html
from util import make_numbers_bold


_LOGGER = logging.getLogger("barahl0bot")


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
        if self.seller:
            seller_id = self.seller.vk_id
        else:
            # in case of group/public/community photo
            seller_id = self.photo.owner_id
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
                comments_str = comments_str[:settings.COMMENTS_STRING_RESTRICTION]
            comments_str = comments_str.lower()
            comments_str = comments_str.replace('\n', ' ')
            comments_str = html.escape(comments_str)
            comments_str = make_numbers_bold(comments_str)

        return comments_str

    def get_description_text(self, _restrict=True):
        text = self.photo.text
        if not text:
            return text

        text = text.lower()
        text = text.replace('\n', ' ')
        if _restrict:
            text = text[:settings.DESCRIPTION_STRING_RESTRICTION]
        text = html.escape(text)
        text = make_numbers_bold(text)

        return text

    def build_message_telegram(self, _channel):
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
        if comments_str and len(comments_str) + len(text) < settings.DESCRIPTION_PLUS_COMMENTS_STRING_RESTRICTION:
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
            latest_product += "<b>Предыдущее объявление:</b> <a href=\"https://t.me/{}/{}\">Telegram</a> | barahloch". \
                format(_channel, self.prev_tg_post)

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

    def get_photo_id_str(self):
        return str(self.owner_id) + "_" + str(self.photo_id)

