from util import bot_util
import sys
import pymysql


if __name__ == "__main__":
    if len(sys.argv) != 2:
        exit(-1)

    albums_file_name = sys.argv[1]
    albums_lines = bot_util.read_lines(albums_file_name)

    ow_al_id_list = []
    for a in albums_lines:
        a = a.rstrip()
        oa_id = a.split('_')
        if len(oa_id) < 2:
            continue
        owner_id = int(oa_id[0])
        album_id = oa_id[1]
        ow_al_id_list.append({'owner_id': owner_id, 'album_id': album_id})

    connection = pymysql.connect(host='localhost', user='fut33v', password='', db='barahlochannel', charset='utf8mb4')

    for a in ow_al_id_list:
        owner_id = a['owner_id']
        album_id = a['album_id']
        print(owner_id, album_id)

        with connection.cursor() as cursor:
            sql = 'INSERT INTO `albums` VALUES(%s, %s);'
            cursor.execute(sql, (owner_id, album_id))

        connection.commit()

