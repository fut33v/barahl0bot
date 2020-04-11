import util

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
            sql = 'INSERT INTO sellers VALUES({}, "{}", "{}", "{}");'.format(vk_id, full_name, city, photo)
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
        print("give me sellers json")
        exit(-1)

    sellers_json = sys.argv[1]

    sellers = util.load_json_file(sellers_json)
    city_ids_set = set()
    cities_list = []
    for s in sellers:
        if 'city' not in s:
            continue
        city_id = s['city']['id']
        city_title = s['city']['title']
        if city_id not in city_ids_set:
            cities_list.append((city_id, city_title))
            city_ids_set.add(city_id)

    for c in cities_list:
        print(c[0], c[1])

        sql = 'INSERT INTO cities VALUES({}, "{}");'. \
            format(c[0], c[1])

        print(sql)

        cur = connection.cursor()
        try:
            cur.execute(sql)
            print("The query affected {} rows".format(cur.rowcount))
        except pymysql.err.IntegrityError as e:
            print(e)
        connection.commit()


