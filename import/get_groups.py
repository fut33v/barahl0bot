import sys
import vk_api
from database import Barahl0botDatabase
from settings import Barahl0botSettings
import pymysql

if __name__ == "__main__":
    if len(sys.argv) != 2:
        exit(-1)

    settings_json = sys.argv[1]

    settings = Barahl0botSettings(settings_json)
    database = Barahl0botDatabase(settings.channel)

    vk_session = vk_api.VkApi(token=settings.token_vk)
    vk = vk_session.get_api()

    albums = database.get_albums_list()
    ow_set = set()
    for a in albums:
        if a.owner_id < 0:
            if a.owner_id not in ow_set:
                ow_set.add(a.owner_id)
                print(a.owner_id)

    ow_list = list(ow_set)
    ow_list = [-x for x in ow_list]
    groups = vk.groups.getById(group_ids=ow_list)

    connection = database.get_connection()
    cur = connection.cursor()
    for g in groups:
        print(g)
        try:
            sql = 'INSERT INTO groups VALUES(%s, %s, %s, %s);'
            cur.execute(sql, (g['id'], g['name'], g['screen_name'], g['photo_200']))
            print("The query affected {} rows".format(cur.rowcount))
        except pymysql.err.IntegrityError as e:
            print(e)

    connection.commit()
