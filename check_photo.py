import hashlib

from util import bot_util


def is_photo_unique(file_name, url):
    photo = bot_util.urlopen(url)
    if not photo:
        return None
    sha = hashlib.sha256()
    sha.update(photo)
    h = sha.hexdigest()
    if not bot_util.check_file_for_string(file_name, h + "\n"):
        return False
    else:
        bot_util.append_string_to_file(file_name, h + "\n")
        return True
