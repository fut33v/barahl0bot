import logging
import pymysql
from structures import Album, Product, Seller

_LOGGER = logging.getLogger("barahl0bot")


class Barahl0botDatabase:
    def __init__(self, _channel):
        self._connection = pymysql.connect(host='localhost', user='fut33v', password='', db='barahlochannel',
                                           charset='utf8mb4')
        self._channel = _channel
        self._albums_table = self._channel + "_albums"
        return

    def get_albums_list(self):
        with self._connection.cursor() as cursor:
            sql = "SELECT * FROM {} ORDER BY owner_id".format(self._albums_table)
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

    def is_album_in_table(self, album):
        with self._connection.cursor() as cursor:
            sql = "SELECT * FROM {t} WHERE owner_id = %s AND album_id = %s;". \
                format(t=self._albums_table)
            #, oi=album.owner_id, ai=album.album_id)
            cursor.execute(sql, (album.owner_id, album.album_id))
            result = cursor.fetchone()
            return result

    def insert_album(self, album):
        try:
            with self._connection.cursor() as cursor:
                sql = 'INSERT INTO {t} (' \
                      'owner_id, ' \
                      'album_id,' \
                      'title,' \
                      'description,' \
                      'photo) ' \
                      'VALUES(%s, %s, %s, %s, %s);'.\
                    format(t=self._albums_table)

                cursor.execute(sql, (album.owner_id, album.album_id, album.title, album.description, album.photo))

            self._connection.commit()
        except pymysql.Error as e:
            print(e)

    def delete_album(self, album):
        with self._connection.cursor() as cursor:
            sql = 'DELETE FROM {t} WHERE owner_id=%s AND album_id=%s;'.format(t=self._albums_table)
            result = cursor.execute(sql, (album.owner_id, album.album_id))
            self._connection.commit()
            return result

    def is_photo_posted_by_hash(self, _hash):
        with self._connection.cursor() as cursor:
            sql = "SELECT `tg_post_id`,`date` FROM `goods` WHERE `hash`=%s AND tg_channel=%s ORDER BY date DESC"
            cursor.execute(sql, (_hash, self._channel))
            result = cursor.fetchone()
            if result:
                return {
                    'date': result[1],
                    'tg_post_id': result[0]
                }
        return False

    def is_photo_posted_by_id(self, _photo):
        photo_id_str = _photo.get_photo_id_str()

        with self._connection.cursor() as cursor:
            # Read a single record
            sql = "SELECT * FROM `goods` WHERE `vk_photo_id`=%s and tg_channel=%s"
            cursor.execute(sql, (photo_id_str, self._channel))
            result = cursor.fetchone()
            if result:
                seller = Seller()
                seller.vk_id = result[2]
                photo_hash = result[6]

                product = Product(seller=seller, photo_hash=photo_hash)
                product.descr = result[3]
                product.comments_text = result[8]
                product.tg_post_id = result[4]

                return product

        return False

    def insert_product(self, _product):
        if not _product.seller and _product.photo.owner_id > 0:
            _LOGGER.warning("Trying to add good without seller")
            return

        # if _product.photo.owner_id < 0:
        # if seller is group/public/community
        if _product.seller.is_club():
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

        descr = _product.get_description_text()
        comments = _product.get_comments_text()

        with self._connection.cursor() as cursor:
            sql = 'INSERT INTO goods (' \
                  'vk_photo_id, ' \
                  'photo_link,' \
                  'seller_id,' \
                  'descr,' \
                  'tg_post_id,' \
                  'date,' \
                  'hash,' \
                  'tg_channel,' \
                  'comments) ' \
                  'VALUES(%s, %s, %s, %s, %s, NOW(), %s, %s, %s);'

            cursor.execute(sql, (
                vk_photo_id, photo_link, seller_id, descr, tg_post_id, photo_hash, self._channel, comments))

        self._connection.commit()

    def update_product_text_and_comments(self, product):
        owner_id = str(product.album.owner_id)
        photo = product.photo
        photo_id = str(photo.photo_id)
        vk_photo_id = owner_id + "_" + photo_id
        text = product.get_description_text()
        comments = product.get_comments_text()
        with self._connection.cursor() as cursor:
            sql = "UPDATE goods SET descr = '{text}', comments = '{comments}' WHERE vk_photo_id = '{vk_photo_id}';".\
                format(vk_photo_id=vk_photo_id, text=text, comments=comments)
            print(sql)
            cursor.execute(sql)
        self._connection.commit()

    def get_connection(self):
        return self._connection

