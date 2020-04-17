import util
import glob
# import barahl0bot
import vk_api
import sys
import os
from settings import Barahl0botSettings

_SETTINGS_JSON_FILENAME = "../settings.json"
_SETTINGS = Barahl0botSettings(_SETTINGS_JSON_FILENAME)
# _SETTINGS = bot_util.load_json_file(_SETTINGS_JSON_FILENAME)
# _TOKEN_VK = _SETTINGS['token_vk']


def parse_json_file(_filename, _already):
    sellers_set = set()

    data = util.load_json_file(_filename)

    for good in data:
        seller = good['seller']

        print(seller)
        print(_filename)
        print(good)

        s = seller.split('/')
        if len(s) == 0:
            continue
        s = s[-1][2:]
        if not s:
            continue
        seller_id = int(s)
        print(seller_id)

        unique = False
        if seller_id not in sellers_set:
            unique = True

        if seller_id not in _already:
            sellers_set.add(seller_id)
        else:
            print(seller_id, "is already in file")
        # use vk api to load user information
        # only if this id is unique

    return sellers_set


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("give me directory with .json files with messages from channel")
        exit(-1)

    already_got_sellers_set = set()
    if len(sys.argv) == 3:
        sellers_json_input = sys.argv[2]
        sellers = util.load_json_file(sellers_json_input)
        if sellers:
            for s in sellers:
                already_got_sellers_set.add(s['id'])

    dir_name = sys.argv[1]
    json_files = glob.glob(os.path.join(dir_name, "messages*.json"))
    print(json_files)

    sellers_id_set = set()

    # f = dir_name + "messages.json"
    for f in json_files:
        sellers_id_set.update(parse_json_file(f, already_got_sellers_set))

    # print(sellers_id_set)
    print(len(sellers_id_set))
    sellers_id_list = list(sellers_id_set)

    vk_session = vk_api.VkApi(token=_TOKEN_VK)
    vk_api = vk_session.get_api()

    sellers_count = len(sellers_id_list)
    number_of_thousands = int(sellers_count / 1000) + 1

    seller_info_list = []

    for i in range(number_of_thousands):
        x = sellers_id_list[i*1000:i*1000+1000]
        print(x)
        sellers = vk_api.users.get(user_ids=x, fields='city,photo_200')
        seller_info_list.extend(sellers)

    bot_util.save_json_file(os.path.join(dir_name, "sellers.json"), seller_info_list)
