from util import bot_util

import pymysql
import glob

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
    dir_name = "../chat_export/"
    sellers_filename = dir_name + "sellers.json"
    sellers = bot_util.load_json_file(sellers_filename)
    # sellers_to_mysql(sellers)

    messages = glob.glob(dir_name + "messages*.json")

    for m in messages:
        print(m)
        goods = bot_util.load_json_file(m)
        for g in goods:
            if len(g['seller']) <= 17:
                continue
            seller_id = int(g['seller'][17:])
            description = g['description']
            vk_photo_id = g['photo'][20:]
            photo_link_jpg = g['photo_link']

            # p = photo_vk_id.split("_")
            # photo_owner_id = p[0]
            # photo_photo_id = p[1]
            description = description.replace('"', "'")
            sql = 'INSERT INTO goods VALUES("{}", "{}", {}, "{}");'.format(vk_photo_id, photo_link_jpg, seller_id, description)
            print(sql)

            print(len(description))

            cur = connection.cursor()
            try:
                cur.execute(sql)
                print("The query affected {} rows".format(cur.rowcount))
            except pymysql.err.IntegrityError as e:
                print(e)

    connection.commit()


