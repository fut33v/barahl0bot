import logging

import pymysql

import psycopg2
from psycopg2.extras import RealDictCursor


import time
from structures import Album, Product, Seller, City, Group
from abc import ABC, abstractmethod


_LOGGER = logging.getLogger("barahl0bot")


def none_if_empty(string):
    if not string:
        return None
    return string


class BarahlochDatabase(ABC):
    def __init__(self, channel):
        self._channel = channel
        self._albums_table = self._channel + "_albums"
        self._goods_table = self._channel + "_goods"
        self._sellers_table = "sellers"
        self._cities_table = "cities"
        self._groups_table = "groups"
        return

    @abstractmethod
    def get_albums_list(self):
        pass

    @abstractmethod
    def is_album_in_table(self, album):
        pass

    @abstractmethod
    def insert_album(self, album):
        pass

    @abstractmethod
    def delete_album(self, album):
        pass

    @abstractmethod
    def is_group_in_table_by_id(self, group_id):
        pass

    @abstractmethod
    def get_group_by_id(self, group_id):
        pass

    @abstractmethod
    def insert_group(self, group):
        pass

    @abstractmethod
    def is_photo_posted_by_hash(self, _hash):
        pass

    @abstractmethod
    def is_photo_posted_by_id(self, photo):
        pass

    @abstractmethod
    def insert_product(self, product):
        pass

    @abstractmethod
    def update_product_text_and_comments(self, product):
        pass

    @abstractmethod
    def get_city_title(self, city_id):
        pass

    @abstractmethod
    def is_seller_in_table_by_id(self, seller_id):
        pass

    @abstractmethod
    def insert_seller(self, seller):
        pass

    @abstractmethod
    def insert_city(self, city):
        pass

    @abstractmethod
    def get_top_cities(self, limit):
        pass


class PostgreBarahlochDatabase(BarahlochDatabase):
    def __init__(self, channel):
        self._connection = psycopg2.connect("dbname={} user=fut33v".format(channel))

        super().__init__(channel)

        self._albums_table = "albums"
        self._goods_table = "goods"

        return

    def _execute(self, cursor, sql, args=tuple()):
        try:
            return cursor.execute(sql, args)
        except Exception as e:
            _LOGGER.error("Problems with psycopg: {}".format(e))
            raise e
            # self._connection.connect()
            # time.sleep(1)
            # return cursor.execute(sql, args)

    def get_albums_list(self):
        sql = "SELECT * FROM {} ORDER BY owner_id".format(self._albums_table)
        with self._connection.cursor(cursor_factory=RealDictCursor) as cursor:
            self._execute(cursor, sql)
            # cursor.execute(sql)
            result = cursor.fetchall()
            if result:
                albums = []
                for a in result:
                    owner_id = a['owner_id']
                    album_id = a['album_id']
                    albums.append(Album(owner_id, album_id))
                return albums
        return False
        pass

    def is_album_in_table(self, album):
        with self._connection.cursor() as cursor:
            sql = "SELECT * FROM {t} WHERE owner_id = %s AND album_id = %s;". \
                format(t=self._albums_table)
            self._execute(cursor, sql, (album.owner_id, album.album_id))
            result = cursor.fetchone()
            return result
        pass

    def insert_album(self, album):
        with self._connection.cursor() as cursor:
            sql = 'INSERT INTO {t} (' \
                  'owner_id, ' \
                  'album_id,' \
                  'title,' \
                  'description,' \
                  'photo) ' \
                  'VALUES(%s, %s, %s, %s, %s);'. \
                format(t=self._albums_table)

            self._execute(cursor, sql, (album.owner_id, album.album_id, album.title, album.description, album.photo))

        self._connection.commit()

    def delete_album(self, album):
        with self._connection.cursor() as cursor:
            sql = 'DELETE FROM {t} WHERE owner_id=%s AND album_id=%s;'.format(t=self._albums_table)
            result = self._execute(cursor, sql, (album.owner_id, album.album_id))
            self._connection.commit()
            return result

    def is_group_in_table_by_id(self, group_id):
        group_id = abs(group_id)
        with self._connection.cursor() as cursor:
            sql = "SELECT * FROM {t} WHERE id=%s".format(t=self._groups_table)
            cursor.execute(sql, (group_id, ))
            result = cursor.fetchone()
            if result:
                return True
        return False

    def get_group_by_id(self, group_id):
        group_id = abs(group_id)
        with self._connection.cursor(cursor_factory=RealDictCursor) as cursor:
            sql = "SELECT * FROM {t} WHERE id=%s".format(t=self._groups_table)
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
            sql = "SELECT tg_post_id, date FROM {t} WHERE hash=%s ORDER BY date DESC".format(t=self._goods_table)
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
                  " FROM {t} WHERE vk_owner_id=%s AND vk_photo_id=%s AND tg_post_id IS NOT NULL".format(t=self._goods_table)
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
        photo_preview_link = none_if_empty(photo.get_preview_photo_url())
        photo_hash = product.photo_hash
        album_id = product.album.album_id
        descr = none_if_empty(product.get_description_text(restrict=False))
        comments = none_if_empty(product.get_comments_text(restrict=False))

        with self._connection.cursor() as cursor:
            sql = 'INSERT INTO {t} (' \
                  'vk_owner_id, ' \
                  'vk_photo_id, ' \
                  'vk_album_id, ' \
                  'photo_link,' \
                  'photo_preview,' \
                  'seller_id,' \
                  'descr,' \
                  'tg_post_id,' \
                  'date,' \
                  'hash,' \
                  'comments) ' \
                  'VALUES(%s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s);'.format(t=self._goods_table)

            cursor.execute(sql, (
                photo.owner_id,
                photo.photo_id,
                album_id,
                photo_link,
                photo_preview_link,
                seller_id,
                descr,
                tg_post_id,
                photo_hash,
                comments))

        self._connection.commit()

    def update_product_text_and_comments(self, product):
        photo = product.photo
        text = none_if_empty(product.get_description_text(restrict=False))
        comments = none_if_empty(product.get_comments_text(restrict=False))
        with self._connection.cursor() as cursor:
            sql = "UPDATE {t} SET descr = %s, comments = %s WHERE vk_owner_id = %s AND vk_photo_id = %s;". \
                format(t=self._goods_table)
            cursor.execute(sql, (text, comments, photo.owner_id, photo.photo_id))
        self._connection.commit()

    def get_city_title(self, city_id):
        with self._connection.cursor(cursor_factory=RealDictCursor) as cursor:
            sql = "SELECT * FROM {t} WHERE id=%s".format(t=self._cities_table)
            cursor.execute(sql, (city_id,))
            result = cursor.fetchone()
            if result:
                return result["title"]
        return False

    def is_seller_in_table_by_id(self, seller_id):
        with self._connection.cursor(cursor_factory=RealDictCursor) as cursor:
            sql = "SELECT * FROM {t} WHERE vk_id=%s".format(t=self._sellers_table)
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

    def insert_city(self, city):
        if not isinstance(city, City):
            return
        with self._connection.cursor() as cursor:
            sql = "SELECT * FROM {t} WHERE id=%s".format(t=self._cities_table)
            cursor.execute(sql, (city.id,))
            result = cursor.fetchone()
            if not result:
                sql = 'INSERT INTO {t} (' \
                      'id, ' \
                      'title) ' \
                      'VALUES(%s, %s);'.format(t=self._cities_table)
                cursor.execute(sql, (city.id, city.title))

    def get_top_cities(self, limit):
        with self._connection.cursor(cursor_factory=RealDictCursor) as cursor:
            sql = \
                "SELECT city_id, count(*) as counter " \
                "FROM {t} " \
                "GROUP BY city_id " \
                "HAVING city_id IS NOT NULL " \
                "ORDER BY counter DESC LIMIT %s".format(t=self._sellers_table)
            self._execute(cursor, sql, (limit, ))
            result = cursor.fetchall()
            if not result:
                return None
            city_ids = [x['city_id'] for x in result]
            sql = "SELECT * from {t} WHERE id IN (%s)".format(t=self._cities_table)
            format_strings = ','.join(['%s'] * len(city_ids))
            self._execute(cursor, sql % format_strings, tuple(city_ids, ))
            result = cursor.fetchall()
            cities = []
            for c in result:
                cities.append(City(c['id'], c['title']))
            return cities


class MysqlBarahlochDatabase(BarahlochDatabase):
    def __init__(self, channel, database='barahlochannel'):
        super().__init__(channel)

        self._albums_table = self._channel + "_albums"
        self._goods_table = self._channel + "_goods"

        self._connection = pymysql.connect(host='localhost', user='fut33v', password='', db=database,
                                           charset='utf8mb4', autocommit=True)
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
        photo_preview_link = photo.get_preview_photo_url()
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
                  'photo_preview,' \
                  'seller_id,' \
                  'descr,' \
                  'tg_post_id,' \
                  'date,' \
                  'hash,' \
                  'comments) ' \
                  'VALUES(%s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s);'.format(t=self._goods_table)

            cursor.execute(sql, (
                photo.owner_id,
                photo.photo_id,
                album_id,
                photo_link,
                photo_preview_link,
                seller_id,
                descr,
                tg_post_id,
                photo_hash,
                comments))

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

    def get_top_cities(self, limit):
        with self._connection.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = \
                "SELECT city_id, count(*) as COUNTER " \
                "FROM {t} " \
                "GROUP BY city_id " \
                "HAVING city_id " \
                "ORDER BY counter DESC LIMIT %s".format(t=self._sellers_table)
            self._execute(cursor, sql, (limit, ))
            result = cursor.fetchall()
            if not result:
                return None
            city_ids = [x['city_id'] for x in result]
            sql = "SELECT * from {t} WHERE id IN (%s)".format(t=self._cities_table)
            format_strings = ','.join(['%s'] * len(city_ids))
            self._execute(cursor, sql % format_strings, tuple(city_ids, ))
            result = cursor.fetchall()
            cities = []
            for c in result:
                cities.append(City(c['id'], c['title']))
            return cities

    def get_connection(self):
        return self._connection


class DatabaseCreator(ABC):

    @abstractmethod
    def factory_method(self, channel):
        pass


class MysqlCreator(DatabaseCreator):
    def factory_method(self, channel) -> MysqlBarahlochDatabase:
        return MysqlBarahlochDatabase(channel)


class PostgreCreator(DatabaseCreator):
    def factory_method(self, channel) -> PostgreBarahlochDatabase:
        return PostgreBarahlochDatabase(channel)


def create_database(creator: DatabaseCreator, channel) -> BarahlochDatabase:
    return creator.factory_method(channel)


def get_database(dbms: str, channel: str) -> BarahlochDatabase:
    if dbms == "mysql":
        return create_database(MysqlCreator(), channel)
    elif dbms == "postgre":
        return create_database(PostgreCreator(), channel)
    else:
        raise Exception("Wrong DBMS")


if __name__ == "__main__":
    postgre_database = create_database(PostgreCreator(), "barahlochannel")

    albums = postgre_database.get_albums_list()
    print(albums)

    print(postgre_database.is_album_in_table(albums[0]))

