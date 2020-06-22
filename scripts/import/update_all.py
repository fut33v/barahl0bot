import sys
import time

import vk_api
import pymysql

from database import Barahl0botDatabase
from settings import Barahl0botSettings
from vkontakte import VkontakteInfoGetter
from structures import Seller, City


def update_albums():
    albums = _DATABASE.get_albums_list()
    for a in albums:
        _VKONTAKTE_GETTER.update_album_info(a)
        try:
            with _CONNECTION.cursor() as cur:
                sql = 'UPDATE {}_albums SET title=%s, description=%s, photo=%s WHERE owner_id=%s and album_id =%s;'. \
                    format(settings.channel)
                cur.execute(sql, (a.title, a.description, a.photo, a.owner_id, a.album_id))
                print("The query affected {} rows".format(cur.rowcount))
            _CONNECTION.commit()
            time.sleep(1)
        except pymysql.err.IntegrityError as e:
            print(e)


def update_sellers_from_goods():
    goods_table = "all_goods"
    with _CONNECTION.cursor() as cursor:
        sql = "SELECT vk_id from sellers;"
        cursor.execute(sql)
        we_have_sellers = cursor.fetchall()

        sql = "SELECT seller_id from {} GROUP BY seller_id;".format(goods_table)
        cursor.execute(sql)
        all_sellers = cursor.fetchall()

    sellers_id_users = \
        [item[0] for item in all_sellers if item not in we_have_sellers and item[0] > 0 and item[0] != 100]
    sellers_id_groups = \
        [item[0] for item in all_sellers if item not in we_have_sellers and item[0] < 0 and item[0] != 100]

    sellers = []

    if sellers_id_users:
        sellers_users = _VKONTAKTE_GETTER.get_sellers(sellers_id_users)
        sellers.extend(sellers_users)
    if sellers_id_groups:
        groups = _VKONTAKTE_GETTER.get_groups(sellers_id_groups)
        sellers_groups = []
        for g in groups:
            s = Seller()
            s.vk_id = -g.id
            s.first_name = g.name
            s.last_name = g.name
            s.photo = g.photo
            sellers_groups.append(s)
        sellers.extend(sellers_groups)

    for s in sellers:
        _DATABASE.insert_seller(s)


def update_groups():
    albums = _DATABASE.get_albums_list()
    ow_set = set()
    for a in albums:
        if a.owner_id < 0:
            if a.owner_id not in ow_set:
                ow_set.add(a.owner_id)

    ow_list = list(ow_set)
    ow_list = [-x for x in ow_list]
    groups = _VK.groups.getById(group_ids=ow_list)

    try:
        with _CONNECTION.cursor() as cur:
            for g in groups:
                sql = 'SELECT * from groups where id = %s'
                result = cur.execute(sql, (g['id']))
                if not result:
                    sql = 'INSERT INTO groups (id, name, screen_name, photo) VALUES(%s, %s, %s, %s);'
                    cur.execute(sql, (g['id'], g['name'], g['screen_name'], g['photo_200']))
                else:
                    sql = 'UPDATE groups SET name=%s, screen_name=%s, photo=%s WHERE id=%s;'
                    cur.execute(sql, (g['name'], g['screen_name'], g['photo_200'], g['id']))
                print("The query affected {} rows".format(cur.rowcount))
    except pymysql.err.IntegrityError as e:
        print(e)

    _CONNECTION.commit()


def get_cities():
    sql = "SELECT city_id FROM sellers WHERE city_id NOT IN (SELECT id FROM cities) ORDER BY city_id;"
    with _CONNECTION.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute(sql)
        city_ids = cur.fetchall()
        city_ids = [c['city_id'] for c in city_ids]
        cities = _VKONTAKTE_GETTER.get_cities(city_ids)

    for c in cities:
        city = City(c['id'], c['title'])
        _DATABASE.insert_city(city)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        exit(-1)

    settings_json = sys.argv[1]

    settings = Barahl0botSettings(settings_json)
    _DATABASE = Barahl0botDatabase(settings.channel)

    _CONNECTION = _DATABASE.get_connection()

    _VK_SESSION = vk_api.VkApi(token=settings.token_vk)
    _VK = _VK_SESSION.get_api()
    _VKONTAKTE_GETTER = VkontakteInfoGetter(settings.token_vk)

    update_albums()
    update_sellers_from_goods()
    update_groups()
    get_cities()

