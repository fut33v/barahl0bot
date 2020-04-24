import logging
import pymysql
import time
from structures import Album, Product, Seller, City, Group

_LOGGER = logging.getLogger("barahl0bot")


class Barahl0botDatabase:
    def __init__(self, channel, database='barahlochannel'):
        self._connection = pymysql.connect(host='localhost', user='fut33v', password='', db=database,
                                           charset='utf8mb4', autocommit=True)
        self._channel = channel
        self._albums_table = self._channel + "_albums"
        self._goods_table = self._channel + "_goods"
        self._sellers_table = "sellers"
        self._cities_table = "cities"
        self._groups_table = "groups"
        return

    def _execute(self, cursor, sql, args=tuple()):
        try:
            return cursor.execute(sql, args)
        except (pymysql.err.OperationalError, pymysql.err.InterfaceError) as e:
            _LOGGER.error("Problems with pyMySQL, reconnect...: {}".format(e))
            self._connection.connect()
            time.sleep(1)
            return cursor.execute(sql, args)

    def get_albums_list(self):
        sql = "SELECT * FROM {} ORDER BY owner_id".format(self._albums_table)
        with self._connection.cursor(pymysql.cursors.DictCursor) as cursor:
            self._execute(cursor, sql)
            result = cursor.fetchall()
            if result:
                albums = []
                for a in result:
                    owner_id = a['owner_id']
                    album_id = a['album_id']
                    albums.append(Album(owner_id, album_id))
                return albums
        return False

    def is_album_in_table(self, album):
        with self._connection.cursor() as cursor:
            sql = "SELECT * FROM {t} WHERE owner_id = %s AND album_id = %s;". \
                format(t=self._albums_table)
            self._execute(cursor, sql, (album.owner_id, album.album_id))
            result = cursor.fetchone()
            return result

    def insert_album(self, album):
        with self._connection.cursor() as cursor:
            sql = 'INSERT INTO {t} (' \
                  'owner_id, ' \
                  'album_id,' \
                  'title,' \
                  'description,' \
                  'photo) ' \
                  'VALUES(%s, %s, %s, %s, %s);'.\
                format(t=self._albums_table)

            self._execute(cursor, sql, (album.owner_id, album.album_id, album.title, album.description, album.photo))

        self._connection.commit()

    def delete_album(self, album):
        with self._connection.cursor() as cursor:
            sql = 'DELETE FROM {t} WHERE `owner_id`=%s AND `album_id`=%s;'.format(t=self._albums_table)
            result = self._execute(cursor, sql, (album.owner_id, album.album_id))
            self._connection.commit()
            return result

    def is_group_in_table_by_id(self, group_id):
        group_id = abs(group_id)
        with self._connection.cursor() as cursor:
            sql = "SELECT * FROM {t} WHERE `id`=%s".format(t=self._groups_table)
            cursor.execute(sql, (group_id, ))
            result = cursor.fetchone()
            if result:
                return True
        return False

    def get_group_by_id(self, group_id):
        group_id = abs(group_id)
        with self._connection.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = "SELECT * FROM {t} WHERE `id`=%s".format(t=self._groups_table)
            cursor.execute(sql, (group_id,))
            result = cursor.fetchone()
            if result:
                g = Group()
                g.id = result['id']
                g.name = result['name']
                g.screen_name = result['screen_name']
                g.photo = result['photo']
                return g
        return None

    def insert_group(self, group):
        with self._connection.cursor() as cursor:
            # insert city if not in table
            # insert seller
            sql = 'INSERT INTO {t} (' \
                  'id, ' \
                  'name,' \
                  'screen_name,' \
                  'photo) ' \
                  'VALUES(%s, %s, %s, %s);'.format(t=self._groups_table)
            cursor.execute(sql, (group.id, group.name, group.screen_name, group.photo))

        self._connection.commit()

    def is_photo_posted_by_hash(self, _hash):
        with self._connection.cursor() as cursor:
            sql = "SELECT `tg_post_id`,`date` FROM {t} WHERE `hash`=%s ORDER BY date DESC".format(t=self._goods_table)
            cursor.execute(sql, (_hash, ))
            result = cursor.fetchone()
            if result:
                return {
                    'date': result[1],
                    'tg_post_id': result[0]
                }
        return False

    def is_photo_posted_by_id(self, photo):
        with self._connection.cursor() as cursor:
            # Read a single record
            sql = "SELECT " \
                  "seller_id," \
                  "descr," \
                  "tg_post_id," \
                  "hash," \
                  "comments" \
                  " FROM {t} WHERE `vk_owner_id`=%s AND `vk_photo_id`=%s AND `tg_post_id` IS NOT NULL".format(t=self._goods_table)
            cursor.execute(sql, (photo.owner_id, photo.photo_id,))
            result = cursor.fetchone()
            if result:
                seller = Seller()
                seller.vk_id = result[0]

                product = Product(seller=seller, photo_hash=result[3])
                product.descr = result[1]
                product.tg_post_id = result[2]
                product.comments_text = result[4]

                return product

        return False

    def insert_product(self, product):
        if not product.seller and product.photo.owner_id > 0:
            _LOGGER.warning("Trying to add good without seller")
            return

        # if seller is group/public/community
        if product.seller.is_club():
            seller_id = product.photo.owner_id
        else:
            seller_id = int(product.seller.vk_id)

        photo = product.photo
        tg_post_id = int(product.tg_post_id)
        photo_link = photo.get_widest_photo_url()
        photo_hash = product.photo_hash
        album_id = product.album.album_id
        descr = product.get_description_text(restrict=False)
        comments = product.get_comments_text(restrict=False)

        with self._connection.cursor() as cursor:
            sql = 'INSERT INTO {t} (' \
                  'vk_owner_id, ' \
                  'vk_photo_id, ' \
                  'vk_album_id, ' \
                  'photo_link,' \
                  'seller_id,' \
                  'descr,' \
                  'tg_post_id,' \
                  'date,' \
                  'hash,' \
                  'comments) ' \
                  'VALUES(%s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s);'.format(t=self._goods_table)

            cursor.execute(sql, (
                photo.owner_id, photo.photo_id, album_id, photo_link, seller_id, descr, tg_post_id, photo_hash, comments))

        self._connection.commit()

    def update_product_text_and_comments(self, product):
        photo = product.photo
        text = product.get_description_text(restrict=False)
        comments = product.get_comments_text(restrict=False)
        with self._connection.cursor() as cursor:
            sql = "UPDATE {t} SET descr = %s, comments = %s WHERE vk_owner_id = %s AND vk_photo_id = %s;".\
                format(t=self._goods_table)
            cursor.execute(sql, (text, comments, photo.owner_id, photo.photo_id))
        self._connection.commit()

    def get_city_title(self, city_id):
        with self._connection.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = "SELECT * FROM {t} WHERE `id`=%s".format(t=self._cities_table)
            cursor.execute(sql, (city_id,))
            result = cursor.fetchone()
            if result:
                return result["title"]
        return False

    def is_seller_in_table_by_id(self, seller_id):
        with self._connection.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = "SELECT * FROM {t} WHERE `vk_id`=%s".format(t=self._sellers_table)
            cursor.execute(sql, (seller_id, ))
            result = cursor.fetchone()
            if result:
                seller = Seller()
                seller.city_id = result["city_id"]
                if seller.city_id:
                    seller.city_title = self.get_city_title(seller.city_id)

                seller.vk_id = result["vk_id"]
                seller.first_name = result["first_name"]
                seller.last_name = result["last_name"]
                seller.photo = result["photo"]
                return seller
        return False

    def insert_seller(self, seller):
        if not isinstance(seller, Seller):
            return
        with self._connection.cursor() as cursor:
            if seller.city_id and seller.city_title:
                city = City(seller.city_id, seller.city_title)
                self.insert_city(city)
            # insert seller
            sql = 'INSERT INTO {t} (' \
                  'vk_id, ' \
                  'first_name,' \
                  'last_name,' \
                  'city_id,' \
                  'photo) ' \
                  'VALUES(%s, %s, %s, %s, %s);'.format(t=self._sellers_table)
            cursor.execute(sql, (seller.vk_id, seller.first_name, seller.last_name, seller.city_id, seller.photo))

        self._connection.commit()

    # insert city if not in table
    def insert_city(self, city):
        if not isinstance(city, City):
            return
        with self._connection.cursor() as cursor:
            sql = "SELECT * FROM {t} WHERE `id`=%s".format(t=self._cities_table)
            cursor.execute(sql, (city.id,))
            result = cursor.fetchone()
            if not result:
                sql = 'INSERT INTO {t} (' \
                      'id, ' \
                      'title) ' \
                      'VALUES(%s, %s);'.format(t=self._cities_table)
                cursor.execute(sql, (city.id, city.title))

    def get_connection(self):
        return self._connection

