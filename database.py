import logging
import pymysql
from structures import Album

_LOGGER = logging.getLogger("barahl0bot")


class Barahl0botDatabase:
    def __init__(self, _channel):
        self._connection = pymysql.connect(host='localhost', user='fut33v', password='', db='barahlochannel',
                                           charset='utf8mb4')
        self._channel = _channel
        return

    def is_photo_posted_by_id(self, _photo):
        photo_id_str = _photo.get_photo_id_str()

        with self._connection.cursor() as cursor:
            # Read a single record
            sql = "SELECT * FROM `goods` WHERE `vk_photo_id`=%s and tg_channel=%s"
            cursor.execute(sql, (photo_id_str, self._channel))
            result = cursor.fetchone()
            if result:
                # print("found by id:", result)
                return True

        return False

    def get_albums_list(self):
        with self._connection.cursor() as cursor:
            albums_table = self._channel + "_albums"
            sql = "SELECT * FROM {}".format(albums_table)
            # cursor.execute(sql, albums_table)
            cursor.execute(sql)
            result = cursor.fetchall()
            if result:
                albums = []
                for a in result:
                    owner_id = a[0]
                    album_id = a[1]
                    albums.append(Album(owner_id, album_id))
                return albums
        return False

    def is_photo_posted_by_hash(self, _hash):
        with self._connection.cursor() as cursor:
            sql = "SELECT `tg_post_id`,`date` FROM `goods` WHERE `hash`=%s and tg_channel=%s ORDER BY date DESC"
            cursor.execute(sql, (_hash, self._channel))
            result = cursor.fetchone()
            if result:
                return {
                    'date': result[1],
                    'tg_post_id': result[0]
                }
        return False

    def insert_product(self, _product):
        if not _product.seller and _product.photo.owner_id > 0:
            _LOGGER.warning("Trying to add good without seller")
            return

        # if seller is group/public/community
        if _product.photo.owner_id < 0:
            seller_id = _product.photo.owner_id
        else:
            seller_id = int(_product.seller.vk_id)

        owner_id = str(_product.album.owner_id)
        photo = _product.photo
        photo_id = str(photo.photo_id)
        vk_photo_id = owner_id + "_" + photo_id
        tg_post_id = int(_product.tg_post_id)
        photo_link = photo.get_widest_photo_url()
        photo_hash = _product.photo_hash

        descr = ""
        descr += _product.get_description_text()
        descr += _product.get_comments_text()

        with self._connection.cursor() as cursor:
            sql = 'INSERT INTO `goods` VALUES(%s, %s, %s, %s, %s, NOW(), %s, %s);'
            cursor.execute(sql, (vk_photo_id, photo_link, seller_id, descr, tg_post_id, photo_hash, self._channel))

        self._connection.commit()
