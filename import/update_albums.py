import sys
import time

import vk_api
from database import Barahl0botDatabase
from settings import Barahl0botSettings
import pymysql


def get_widest_photo_url(photo_sizes):
    photo_url = None
    max_width = 0
    for photo_size in photo_sizes:
        width = photo_size['width']
        if width > max_width:
            photo_url = photo_size['src']
            max_width = width
    return photo_url


if __name__ == "__main__":
    if len(sys.argv) != 2:
        exit(-1)

    settings_json = sys.argv[1]

    settings = Barahl0botSettings(settings_json)
    database = Barahl0botDatabase(settings.channel)
    connection = database.get_connection()
    cur = connection.cursor()

    vk_session = vk_api.VkApi(token=settings.token_vk)
    vk = vk_session.get_api()

    albums = database.get_albums_list()
    ow_set = set()
    for a in albums:
        album_info = vk.photos.getAlbums(owner_id=a.owner_id, album_ids=a.album_id, need_covers=1, photo_sizes=1)
        if 'items' not in album_info:
            continue
        album_info = album_info['items'][0]
        print(album_info)
        try:
            sql = 'UPDATE {}_albums SET title=%s, description=%s, photo=%s WHERE owner_id=%s and album_id =%s;'.\
                format(settings.channel)
            photo_url = get_widest_photo_url(album_info["sizes"])
            cur.execute(sql, (album_info["title"], album_info["description"], photo_url, a.owner_id, a.album_id))
            print("The query affected {} rows".format(cur.rowcount))
        except pymysql.err.IntegrityError as e:
            print(e)

        connection.commit()
        time.sleep(1)


