import logging
import html

from .util import get_unix_timestamp
from .settings import COMMENTS_STRING_RESTRICTION, DESCRIPTION_STRING_RESTRICTION, DESCRIPTION_PLUS_COMMENTS_STRING_RESTRICTION


_LOGGER = logging.getLogger("barahl0bot")


class Album:
    _ALBUM_ID_WALL = "wall"

    def __init__(self, _owner_id, _album_id):
        self.owner_id = int(_owner_id)
        self.album_id = int(_album_id)

        self.title = None
        self.description = None
        self.photo = None

        self.group_name = None

    def build_url(self):
        return "https://vk.com/album{}_{}".format(self.owner_id, self.album_id)


class Seller:
    def __init__(self, users_get_result=None):
        self.vk_id = None
        self.first_name = None
        self.last_name = None
        self.city_id = None
        self.photo = None

        self.city_title = None

        if users_get_result:
            if "id" in users_get_result:
                self.vk_id = users_get_result["id"]
            if "first_name" in users_get_result:
                self.first_name = users_get_result["first_name"]
            if "last_name" in users_get_result:
                self.last_name = users_get_result["last_name"]
            if "city" in users_get_result:
                if "title" in users_get_result["city"]:
                    self.city_title = users_get_result["city"]["title"]
                if "id" in users_get_result["city"]:
                    self.city_id = users_get_result["city"]["id"]
            if "photo_200" in users_get_result:
                self.photo = users_get_result["photo_200"]

    def is_club(self):
        if self.vk_id < 0:
            return True
        return False

    def build_url(self):
        if self.is_club():
            return "https://vk.com/public" + str(-self.vk_id)
        return "https://vk.com/id" + str(self.vk_id)


class Product:
    def __init__(self, album=None, photo=None, comments=None, seller=None, photo_hash=None):
        self.album = album
        self.photo = photo
        self.comments = comments
        self.seller = seller
        self.photo_hash = photo_hash

        self.is_duplicate = False
        self.prev_tg_post = None
        self.prev_tg_date = None

        self.descr = None
        self.comments_text = None
        self.state = None
        self.photo_link = None

        self.tg_post_id = None

        if self.comments:
            self.comments_text = self.get_comments_text(self.comments)

    def get_comments_text(self, restrict=True, with_new_lines=False, from_db=False):
        if from_db:
            comments_str = self.comments_text
        else:
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
            if restrict:
                comments_str = comments_str[:COMMENTS_STRING_RESTRICTION]
            if not with_new_lines:
                comments_str = comments_str.replace('\n', ' ')
            comments_str = html.escape(comments_str)

        return comments_str

    def get_description_text(self, restrict=True, with_new_lines=False, from_db=False):
        if from_db:
            text = self.descr
        else:
            text = self.photo.text

        if not text:
            return text

        if not with_new_lines:
            text = text.replace('\n', ' ')
        if restrict:
            text = text[:DESCRIPTION_STRING_RESTRICTION]
        text = html.escape(text)

        return text

    def build_message_telegram(self, channel: str, website: str, from_db=False):
        photo = self.photo
        if from_db:
            photo_url = self.photo_link
        else:
            photo_url = photo.get_widest_photo_url()

        if not from_db:
            owner_id = self.album.owner_id
            group_name = self.album.group_name
            album_name = self.album.title

        seller = self.seller

        if from_db and self.state == 'SOLD':
            latest_product = "ФОТО ВК УДАЛЕНО (СНЯТО С ПРОДАЖИ)\n" + photo_url + "\n"
        else:
            latest_product = "<a href=\"{}\">свободу политзаключенным</a>\n".format(photo_url)

        if not from_db:
            if owner_id > 0:
                latest_product += "<b>{} {}/{}</b>\n\n".format(seller.first_name, seller.last_name, album_name)
            elif album_name and group_name:
                latest_product += "<b>{}/{}</b>\n\n".format(group_name, album_name)

        text = self.get_description_text(from_db=from_db, with_new_lines=True)
        if text:
            latest_product += "<b>Описание:</b> " + text + "\n\n"

        comments_str = self.get_comments_text(from_db=from_db, with_new_lines=True)
        if comments_str and len(comments_str) + len(text) < DESCRIPTION_PLUS_COMMENTS_STRING_RESTRICTION:
            latest_product += "<b>Каменты:</b> " + comments_str + "\n\n"

        # _OWNER_ID_POST_BY_GROUP_ADMIN
        if self.seller.is_club():
            latest_product += \
                "<b>Продавец:</b> <a href=\"https://vk.com/club{}\">{}</a>".format(
                    -owner_id, group_name)
        else:
            latest_product += \
                "<b>Продавец:</b> <a href=\"https://vk.com/id{}\">{} {}</a>".format(
                    seller.vk_id, seller.first_name, seller.last_name)

            if seller.city_title:
                latest_product += " ({})".format(seller.city_title)

        latest_product += "\n"

        if not from_db:
            latest_product += "<b>Фото:</b> {}\n".format(photo.build_url())

        if self.is_duplicate and self.prev_tg_post:
            latest_product += \
                "<b>Предыдущее объявление:</b> " \
                "<a href=\"https://t.me/{}/{}\">Telegram</a> | <a href=\"{}goods/hash/{}\">barahloch</a> \n". \
                    format(channel, self.prev_tg_post, website, self.photo_hash)

        latest_product += "<b>История продавца:</b> <a href=\"{}seller/{}\">тут</a>\n".format(website, seller.vk_id)

        return latest_product

    def is_same_comments_and_descr(self, product_from_db):
        my_comments = self.get_comments_text(restrict=False)
        other_comments = product_from_db.get_comments_text(restrict=False, from_db=True)
        same_comments = my_comments == other_comments

        my_descr = self.get_description_text(restrict=False)
        other_descr = product_from_db.get_description_text(restrict=False, from_db=True)
        same_text = my_descr == other_descr

        # if None and empty string
        if not same_text and not my_descr and not other_descr:
            same_text = True
        if not same_comments and not my_comments and not other_comments:
            same_comments = True

        return same_comments and same_text


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

    def get_preview_photo_url(self):
        if self.sizes[-2]['width'] < 500:
            return None
        photo_url = self.sizes[-2]['url']
        return photo_url

    def get_photo_id_str(self):
        return str(self.owner_id) + "_" + str(self.photo_id)

    def get_photo_age(self):
        now_timestamp = get_unix_timestamp()
        return now_timestamp - self.date


class Group:
    def __init__(self, groups_get_by_id_result=None):
        self.id = None
        self.name = None
        self.screen_name = None
        self.photo = None

        if groups_get_by_id_result:
            if "id" in groups_get_by_id_result:
                self.id = groups_get_by_id_result["id"]
            if "name" in groups_get_by_id_result:
                self.name = groups_get_by_id_result["name"]
            if "screen_name" in groups_get_by_id_result:
                self.screen_name = groups_get_by_id_result["screen_name"]
            if "photo_200" in groups_get_by_id_result:
                self.photo = groups_get_by_id_result["photo_200"]


class City:
    def __init__(self, city_id, title):
        self.id = city_id
        self.title = title
        self.area = None
        self.region = None


class TelegramSeller:
    def __init__(self, tg_id: int, full_name: str, username: str, tg_chat_id: int, city: City):
        self.tg_id = tg_id
        self.tg_chat_id = tg_chat_id
        self.full_name = full_name
        self.username = username
        self.city = city


class TelegramProduct:
    def __init__(self,
                 seller: TelegramSeller,
                 tg_post_id: int,
                 photo_link: str,
                 caption: str,
                 descr: str,
                 category,
                 currency,
                 price: int,
                 ship,
                 photo_hash: str,
                 vk_owner_id: int,
                 vk_photo_id: int):
        self.seller = seller
        self.tg_post_id = tg_post_id

        self.photo_link = photo_link

        self.caption = caption
        self.descr = descr

        self.category = category
        self.currency = currency
        self.price = price
        self.ship = ship

        self.photo_hash = photo_hash

        self.vk_owner_id = vk_owner_id
        self.vk_photo_id = vk_photo_id
