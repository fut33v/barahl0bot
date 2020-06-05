import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from structures import Album, Product, Seller, City, Group, TelegramSeller, TelegramProduct, Photo

_LOGGER = logging.getLogger("barahl0bot")


def none_if_empty(string):
    if not string:
        return None
    return string


class PostgreBarahlochDatabase:

    def __init__(self, channel):
        self._connection = psycopg2.connect("dbname={} user=fut33v".format(channel))
        self._channel = channel

        self._albums_table = self._channel + "_albums"
        self._goods_table = self._channel + "_goods"
        self._sellers_table = "sellers"
        self._cities_table = "cities"
        self._groups_table = "groups"

        self._tg_sellers_table = "tg_sellers"
        self._tg_goods_table = "tg_goods"

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
            cursor.execute(sql, (group_id,))
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
            cursor.execute(sql, (_hash,))
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
                  " FROM {t} WHERE vk_owner_id=%s AND vk_photo_id=%s AND tg_post_id IS NOT NULL".format(
                t=self._goods_table)
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

    def get_goods_with_state_show_ids(self):
        ids_list = []
        with self._connection.cursor(cursor_factory=RealDictCursor) as cursor:
            sql = "SELECT * FROM {t} WHERE state='SHOW' ORDER BY date".format(t=self._goods_table)
            cursor.execute(sql)
            result = cursor.fetchall()
            if result:
                for g in result:
                    ids_list.append((g['vk_owner_id'], g['vk_photo_id']))
        return ids_list

    def get_product_by_owner_photo_id(self, owner_id: int, photo_id: int):
        with self._connection.cursor(cursor_factory=RealDictCursor) as cursor:
            sql = "SELECT * FROM {t} WHERE vk_owner_id=%s AND vk_photo_id=%s".format(t=self._goods_table)
            cursor.execute(sql, (owner_id, photo_id,))
            result = cursor.fetchone()
            if result:
                product = Product()
                product.seller = self.get_seller_by_id(result['seller_id'])
                product.descr = result['descr']
                product.comments_text = result['comments']
                product.tg_post_id = result['tg_post_id']
                product.photo_hash = result['hash']
                product.state = result['state']
                product.photo_link = result['photo_link']
                # todo: select all with that hash and count > 1 duplicate
                # prev_by_hash = self.is_photo_posted_by_hash(product.photo_hash)
                # if prev_by_hash:
                #     is_duplicate = True
                # else:
                #     is_duplicate = False
                # product.is_duplicate = is_duplicate
                return product
        return None

    def set_good_sold(self, owner_id: int, photo_id: int):
        with self._connection.cursor() as cursor:
            sql = "UPDATE {t} SET state='SOLD' WHERE vk_owner_id=%s AND vk_photo_id=%s".format(t=self._goods_table)
            cursor.execute(sql, (owner_id, photo_id,))
        self._connection.commit()

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
        descr = none_if_empty(product.get_description_text(restrict=False, with_new_lines=True))
        comments = none_if_empty(product.get_comments_text(restrict=False, with_new_lines=True))

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

    # TODO: to get_city
    def get_city_title(self, city_id):
        with self._connection.cursor(cursor_factory=RealDictCursor) as cursor:
            sql = "SELECT * FROM {t} WHERE id=%s".format(t=self._cities_table)
            cursor.execute(sql, (city_id,))
            result = cursor.fetchone()
            if result:
                return result["title"]
        return False

    def get_seller_by_id(self, seller_id):
        with self._connection.cursor(cursor_factory=RealDictCursor) as cursor:
            sql = "SELECT * FROM {t} WHERE vk_id=%s".format(t=self._sellers_table)
            cursor.execute(sql, (seller_id,))
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

    def insert_seller(self, seller: Seller):
        with self._connection.cursor() as cursor:
            if seller.city_id and seller.city_title:
                city = City(seller.city_id, seller.city_title)
                self.insert_city(city)
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
            self._execute(cursor, sql, (limit,))
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

    def get_tg_seller_by_id(self, tg_seller_id: int):
        with self._connection.cursor(cursor_factory=RealDictCursor) as cursor:
            sql = "SELECT * FROM {t} WHERE tg_user_id=%s".format(t=self._tg_sellers_table)
            cursor.execute(sql, (tg_seller_id,))
            result = cursor.fetchone()
            if result:
                city_title = self.get_city_title(result['city_id'])
                city = City(city_id=result['city_id'], title=city_title)
                tg_seller = TelegramSeller(tg_id=result['tg_user_id'],
                                           tg_chat_id=result['tg_chat_id'],
                                           full_name=result['full_name'],
                                           username=result['username'],
                                           city=city)
                return tg_seller
        return False

    def insert_tg_seller(self, tg_seller: TelegramSeller):
        with self._connection.cursor() as cursor:
            # if no city like this then insert it
            if not self.get_city_title(tg_seller.city.id):
                self.insert_city(tg_seller.city)
            sql = 'INSERT INTO {t} (' \
                  'tg_user_id, ' \
                  'tg_chat_id,' \
                  'full_name,' \
                  'username,' \
                  'city_id) ' \
                  'VALUES(%s, %s, %s, %s, %s);'.format(t=self._tg_sellers_table)
            cursor.execute(sql, (tg_seller.tg_id,
                                 tg_seller.tg_chat_id,
                                 tg_seller.full_name,
                                 tg_seller.username,
                                 tg_seller.city.id))
        self._connection.commit()

    def insert_tg_product(self, tg_product: TelegramProduct):
        with self._connection.cursor() as cursor:
            # insert seller if not in table
            if not self.get_tg_seller_by_id(tg_product.seller.tg_id):
                self.insert_tg_seller(tg_product.seller)

            sql = 'INSERT INTO {t} (' \
                  'tg_user_id, ' \
                  'tg_post_id, ' \
                  'photo_link,' \
                  'caption,' \
                  'descr,' \
                  'hash,' \
                  'category,' \
                  'price,' \
                  'currency,' \
                  'ship,' \
                  'vk_owner_id,' \
                  'vk_photo_id,' \
                  'date) ' \
                  'VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW());'.format(t=self._tg_goods_table)

            cursor.execute(sql, (
                tg_product.seller.tg_id,
                tg_product.tg_post_id,
                tg_product.photo_link,
                tg_product.caption,
                tg_product.descr,
                tg_product.photo_hash,
                tg_product.category.name,
                tg_product.price,
                tg_product.currency.name,
                tg_product.ship.name,
                tg_product.vk_owner_id,
                tg_product.vk_photo_id
            ))

        self._connection.commit()

        pass


def get_database(dbms: str, channel: str) -> PostgreBarahlochDatabase:
    return PostgreBarahlochDatabase(channel)


if __name__ == "__main__":
    postgre_database = get_database("", "barahl0")
    p = postgre_database.get_product_by_owner_photo_id(-10698066, 457330012)
    print(p)

    # albums = postgre_database.get_albums_list()
    # print(albums)
    #
    # print(postgre_database.is_album_in_table(albums[0]))
    #
    # test_city = City(city_id=35, title="Novgorod")
    # seller = TelegramSeller(tg_id=228,
    #                         tg_chat_id=228,
    #                         full_name="peedor",
    #                         username="peedor228",
    #                         city=test_city)
    #
    # from barahl0bot import BikesCategoryEnum, CurrencyEnum, ShippingEnum
    #
    # test_tg_product = TelegramProduct(seller=seller,
    #                                   tg_post_id=2289,
    #                                   photo_link="xyu",
    #                                   caption="pasdf",
    #                                   descr="aasdfasd",
    #                                   category=BikesCategoryEnum.FIX,
    #                                   currency=CurrencyEnum.EUR,
    #                                   price=228,
    #                                   ship=ShippingEnum.DO_NOT_SHIP,
    #                                   photo_hash="bb72db68ecddcb393305e5997144d9fa3128d2cf4239e5f228b504e5f1c3cc96",
    #                                   vk_owner_id=12345,
    #                                   vk_photo_id=54321)
    #
    # postgre_database.insert_tg_product(test_tg_product)
