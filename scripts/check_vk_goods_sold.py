import time

import psycopg2
from psycopg2.extras import RealDictCursor

from settings import Barahl0botSettings
import sys
import vk_api


def get_show_ids():
    ids_list = []
    with CONNECTION.cursor(cursor_factory=RealDictCursor) as cursor:
        sql = "SELECT * FROM {t} WHERE state='SHOW' ORDER BY date".format(t=DBTABLE)
        cursor.execute(sql)
        result = cursor.fetchall()
        if result:
            for g in result:
                ids_list.append((g['vk_owner_id'], g['vk_photo_id']))
    return ids_list


def set_good_sold(owner_id: int, photo_id: int):
    with CONNECTION.cursor() as cursor:
        sql = "UPDATE {t} SET state='SOLD' WHERE vk_owner_id=%s AND vk_photo_id=%s".format(t=DBTABLE)
        cursor.execute(sql, (owner_id, photo_id,))
    CONNECTION.commit()


def check_is_sold(owner_id: int, photo_id: int) -> bool:
    full_photo_id = "{}_{}".format(owner_id, photo_id)
    try:
        vk.photos.getById(photos=full_photo_id)
    except vk_api.exceptions.ApiError as e:
        if e.code == 200:
            return True
    return False


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("give me json with settings as argument!")
        exit(-1)

    settings_filename = sys.argv[1]
    _SETTINGS = Barahl0botSettings(settings_filename)

    DBNAME = 'barahl0'
    DBUSER = 'fut33v'
    DBTABLE = 'goods'
    CONNECTION = psycopg2.connect("dbname={} user={}".format(DBNAME, DBUSER))

    show_ids = get_show_ids()
    # get 'SHOW' products from database first
    # check every product for

    vk_session = vk_api.VkApi(token=_SETTINGS.token_vk)
    vk = vk_session.get_api()

    for ow_ph in show_ids:
        time.sleep(2)
        if check_is_sold(ow_ph[0], ow_ph[1]):
            print('https://vk.com/photo{}_{}'.format(ow_ph[0], ow_ph[1]), "SOLD!")
            set_good_sold(ow_ph[0], ow_ph[1])
        else:
            print('https://vk.com/photo{}_{}'.format(ow_ph[0], ow_ph[1]), "NOT SOLD!")


