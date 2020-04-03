from util import bot_util

import pymysql
import glob
import sys
import os

connection = pymysql.connect(host='localhost', user='fut33v', password='', db='barahlochannel', charset='utf8mb4')


def sellers_to_mysql(sellers):
    cur = connection.cursor()
    cur.execute("SET NAMES utf8mb4")

    for s in sellers:
        city = ""
        if 'city' in s:
            city = s['city']['title']
        full_name = s['first_name'] + " " + s['last_name']
        photo = ""
        if 'photo_200' in s:
            photo = s['photo_200']
        vk_id = int(s['id'])

        try:
            sql = 'INSERT INTO sellers VALUES({}, "{}", "{}", {}, "{}");'.format(vk_id, full_name, city, 0, photo)
            print(sql)
            cur.execute(sql)
            print("The query affected {} rows".format(cur.rowcount))
        except pymysql.err.IntegrityError as e:
            print(e)

        # finally:
        #     connection.close()

    connection.commit()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("give me directory with .json files (with hash) with messages from channel")
        exit(-1)

    dir_name = sys.argv[1]

    messages = glob.glob(os.path.join(dir_name, "messages*hash.json"))

    # sellers_filename = os.path.join(dir_name, "sellers.json")
    # sellers = bot_util.load_json_file(sellers_filename)
    # sellers_to_mysql(sellers)

    for messages_json_filename in messages:
        print(messages_json_filename)
        goods = bot_util.load_json_file(messages_json_filename)
        for g in goods:
            if len(g['seller']) <= 17:
                continue
            seller_id = int(g['seller'][17:])

            description = g['description']
            description = description.replace('"', "'")

            vk_photo_id = g['photo'][20:]
            photo_link_jpg = g['photo_link']

            tg_post_id = g['message_id']
            date = bot_util.tg_date_to_mysql(g['date'])

            photo_hash = g['hash']

            sql = 'INSERT INTO goods VALUES("{}", "{}", {}, "{}", {}, "{}", "{}");'.\
                format(vk_photo_id, photo_link_jpg, seller_id, description, tg_post_id, date, photo_hash)

            print(sql)

            print(len(description))

            cur = connection.cursor()
            try:
                cur.execute(sql)
                print("The query affected {} rows".format(cur.rowcount))
            except pymysql.err.IntegrityError as e:
                print(e)

    connection.commit()


