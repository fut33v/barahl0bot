import hashlib

from util import bot_util

md5a = hashlib.md5()
md5b = hashlib.md5()


def is_photo_unique(file_name, url):
    photo = bot_util.urlopen(url)
    if not photo:
        return None
    md5 = hashlib.md5()
    md5.update(photo)
    h = md5.hexdigest()
    if not bot_util.check_file_for_string(file_name, h + "\n"):
        return False
    else:
        bot_util.append_string_to_file(file_name, h + "\n")
        return True

