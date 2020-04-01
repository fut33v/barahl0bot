from util import bot_util

import pymysql
import glob

connection = pymysql.connect(host='localhost', user='fut33v', password='', db='barahlochannel', charset='utf8mb4')

if __name__ == "__main__":
    dir_name = "../chat_export/"
    sellers_filename = dir_name + "sellers.json"
    sellers = bot_util.load_json_file(sellers_filename)

    messages = glob.glob(dir_name + "messages*hash.json")

    for m in messages:
        print(m)
        goods = bot_util.load_json_file(m)
        for g in goods:
            if len(g['seller']) <= 17:
                continue
            vk_photo_id = g['photo'][20:]
            tg_message_id = g['message_id']
            date = bot_util.tg_date_to_mysql(g['date'])
            photo_hash = g['hash']

            # sql = "UPDATE goods SET tg_post_id = {_tg_id}, date = '{_date}' WHERE vk_photo_id = '{_vk_id}';".\
            #     format(_tg_id=tg_message_id, _vk_id=vk_photo_id, _date=date)

            sql = "UPDATE goods SET hash = '{_hash}' WHERE vk_photo_id = '{_vk_id}';". \
                format(_hash=photo_hash, _vk_id=vk_photo_id)

            print(sql)

            cur = connection.cursor()
            try:
                cur.execute(sql)
                print("The query affected {} rows".format(cur.rowcount))
            except pymysql.err.IntegrityError as e:
                print(e)

    connection.commit()


