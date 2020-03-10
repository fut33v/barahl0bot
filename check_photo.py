import hashlib
import os

from util import bot_util


def check_photo_hash(file_name, url):
    photo = bot_util.urlopen(url)
    if not photo:
        return None
    sha = hashlib.sha256()
    sha.update(photo)
    h = sha.hexdigest()
    if not bot_util.check_file_for_string(file_name, h + "\n"):
        return False
    else:
        return h


def add_photo_hash(file_name, _photo_hash):
    bot_util.append_string_to_file(file_name, _photo_hash + "\n")


def add_photo_to_last(_file_name, _owner_id, _photo_id, _restriction):
    photo_id_string = str(_owner_id) + '_' + str(_photo_id) + '\n'
    if os.path.exists(_file_name):
        f = open(_file_name, 'r')
        lines = f.readlines()
        f.close()
        if len(lines) > _restriction:
            lines = lines[-_restriction:]
        f = open(_file_name, 'w')
        f.writelines(lines)
        f.close()

    open(_file_name, 'a').write(photo_id_string)


def is_photo_in_last(_file_name, _owner_id, _photo_id):
    if not os.path.exists(_file_name):
        return False
    photo_id_string = str(_owner_id) + '_' + str(_photo_id) + '\n'
    f = open(_file_name, 'r')
    lines = f.readlines()
    result = photo_id_string in lines
    f.close()
    return result


if __name__ == "__main__":
    for i in range(10):
        add_photo_to_last('data/last', -667, 123+i, 5)

    for i in range(10):
        print(is_photo_in_last('data/last', -667, 123+i))


