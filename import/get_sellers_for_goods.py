import sys
import time

import vk_api
import pymysql
from database import Barahl0botDatabase
from settings import Barahl0botSettings
from vkontakte import VkontakteInfoGetter
from structures import Seller

if __name__ == "__main__":
    if len(sys.argv) != 2:
        exit(-1)

    settings_json = sys.argv[1]

    settings = Barahl0botSettings(settings_json)
    database = Barahl0botDatabase(settings.channel, database='barahlochannel')
    connection = database.get_connection()
    vkontakte_getter = VkontakteInfoGetter(settings.token_vk)
    vk_session = vk_api.VkApi(token=settings.token_vk)
    vk_api = vk_session.get_api()

    goods_table = "all_goods"
    with connection.cursor() as cursor:
        sql = "SELECT vk_id from sellers;"
        cursor.execute(sql)
        we_have_sellers = cursor.fetchall()

        sql = "SELECT seller_id from {} GROUP BY seller_id;".format(goods_table)
        cursor.execute(sql)
        all_sellers = cursor.fetchall()

    sellers_id_list = [item[0] for item in all_sellers if item not in we_have_sellers and item[0] > 0 and item[0] != 100]
    sellers_count = len(sellers_id_list)
    number_of_thousands = int(sellers_count / 1000) + 1

    seller_info_list = []
    for i in range(number_of_thousands):
        x = sellers_id_list[i*1000:i*1000+1000]
        print(x)
        sellers = vk_api.users.get(user_ids=x, fields='city,photo_200')
        seller_info_list.extend(sellers)

    for s in seller_info_list:
        seller = Seller(s)
        database.insert_seller(seller)


