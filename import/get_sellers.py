from util import bot_util
import glob
import barahl0bot
import vk_api


def parse_json_file(_filename):
    data = bot_util.load_json_file(_filename)

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
        if seller_id not in sellers_id_set:
            unique = True
        sellers_id_set.add(seller_id)
        # use vk api to load user information
        # only if this id is unique


if __name__ == "__main__":
    dir_name = "../chat_export/"
    json_files = glob.glob(dir_name + "*.json")
    print(json_files)

    sellers_id_set = set()

    # f = dir_name + "messages.json"
    for f in json_files:
        parse_json_file(f)

    # print(sellers_id_set)
    print(len(sellers_id_set))
    sellers_id_list = list(sellers_id_set)

    vk_session = vk_api.VkApi(token=barahl0bot.TOKEN_VK)
    vk_api = vk_session.get_api()

    sellers_count = len(sellers_id_list)
    number_of_thousands = int(sellers_count / 1000) + 1

    seller_info_list = []

    for i in range(number_of_thousands):
        x = sellers_id_list[i*1000:i*1000+1000]
        print(x)
        sellers = vk_api.users.get(user_ids=x, fields='city,photo_200')
        seller_info_list.append(sellers)

    bot_util.save_json_file(dir_name + "sellers.json", seller_info_list)
