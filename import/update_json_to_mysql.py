from util import bot_util

import pymysql
import glob

connection = pymysql.connect(host='localhost', user='fut33v', password='', db='barahlochannel', charset='utf8mb4')

if __name__ == "__main__":
    dir_name = "../chat_export/"
    sellers_filename = dir_name + "sellers.json"
    sellers = bot_util.load_json_file(sellers_filename)

    messages = glob.glob(dir_name + "messages*.json")

    for m in messages:
        print(m)
        goods = bot_util.load_json_file(m)
        for g in goods:
            if len(g['seller']) <= 17:
                continue
            vk_photo_id = g['photo'][20:]
            tg_message_id = g['message_id']

            date = g['date']
            ds = date.split(' ')
            dmy = ds[0].split('.')
            hms = ds[1]
            # YYYY-MM-DD hh:mm:ss
            date = "{}-{}-{} {}".format(dmy[2], dmy[1], dmy[0], hms)

            sql = "UPDATE goods SET tg_post_id = {_tg_id}, date = '{_date}' WHERE vk_photo_id = '{_vk_id}';".\
                format(_tg_id=tg_message_id, _vk_id=vk_photo_id, _date=date)

            # update goods set tg_post_id = 666  where vk_photo_id = '-103775110_456241546';
            print(sql)

            cur = connection.cursor()
            try:
                cur.execute(sql)
                print("The query affected {} rows".format(cur.rowcount))
            except pymysql.err.IntegrityError as e:
                print(e)

    connection.commit()


