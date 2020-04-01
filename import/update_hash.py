import glob
import hashlib
from util import bot_util


def get_photo_hash(_url):
    photo = bot_util.urlopen(_url)
    if not photo:
        return None
    sha = hashlib.sha256()
    sha.update(photo)
    h = sha.hexdigest()
    return h


if __name__ == "__main__":
    dir_name = "../chat_export/"
    # messages = glob.glob(dir_name + "messages*.json")
    messages = [dir_name + "messages35.json"]

    for m in messages:
        print(m)
        goods = bot_util.load_json_file(m)
        goods_count = len(goods)
        i = 0
        for g in goods:
            if len(g['seller']) <= 17:
                continue
            photo_link_jpg = g['photo_link']
            photo_hash = get_photo_hash(photo_link_jpg)
            g['hash'] = photo_hash
            print(i, "/", goods_count, " ", photo_hash)
            i += 1

        bot_util.save_json_file(m+'.hash.json', goods)
