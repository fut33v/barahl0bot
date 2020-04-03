import glob
import hashlib
import os
import sys
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
    if len(sys.argv) < 2:
        print("give me directory with .json files with messages from channel")
        exit(-1)

    dir_name = sys.argv[1]
    messages = glob.glob(os.path.join(dir_name, "messages*.json"))

    for messages_json_filename in messages:
        print(messages_json_filename)
        goods = bot_util.load_json_file(messages_json_filename)
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

        json_filename = os.path.splitext(messages_json_filename)[0] + "_hash.json"
        bot_util.save_json_file(json_filename, goods)
        os.remove(messages_json_filename)
