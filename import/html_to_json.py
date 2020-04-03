from bs4 import BeautifulSoup, NavigableString, Tag
import re
import glob
import sys
import os

from util import bot_util


def process_html(_filename):
    html_doc = open(_filename, 'r').read()
    soup = BeautifulSoup(html_doc, 'html.parser')

    photo_link_regexp = re.compile("jpg")
    seller_regexp = re.compile("Продавец")
    photo_regexp = re.compile("Фото")
    descr_regexp = re.compile("Описание")
    comments_regexp = re.compile("Каменты")
    id_regexp = re.compile("id")
    message_regexp = re.compile("message")

    goods_list = []
    messages = soup.find_all("div", class_="message default clearfix")
    for m in messages:
        message_text = m.find("div", class_="text")
        if not message_text:
            print("not found 'text' in message div")
            continue

        without_br = [x for x in message_text.contents if x.name != 'br']

        i = 0
        photo_link = None
        for x in without_br:
            i += 1
            if x.name == 'a':
                photo_link = x.text
                break
        without_br = without_br[i:]

        if not photo_link:
            continue

        if not photo_link_regexp.search(photo_link):
            continue

        description = ""
        seller = None
        photo = None
        seller_next = False
        photo_next = False
        description_state = False
        for x in without_br:
            strong = (isinstance(x, Tag) and x.name == "strong")
            if isinstance(x, NavigableString) or strong:
                if strong:
                    x = x.text
                if descr_regexp.search(x):
                    if not strong:
                        description = x
                    else:
                        description_state = True
                        # description = ""
                if seller_regexp.search(x):
                    description_state = False
                    seller_next = True
                if photo_regexp.search(x):
                    description_state = False
                    photo_next = True
                if comments_regexp.search(x):
                    description_state = True

                if description_state:
                    description += x

            else:
                if description_state:
                    description += x.text
                if seller_next:
                    seller = x.get('href')
                    seller_next = False
                if photo_next:
                    photo = x.get('href')
                    photo_next = False

        if not seller or not id_regexp.search(seller):
            print(_filename, without_br, "\n\n")
            continue

        date = None
        date_div = m.find("div", class_="date")
        if date_div:
            date_string = date_div.get('title')
            date = date_string

        message_id = None
        message_id_text = m.get('id')
        if message_regexp.match(message_id_text):
            message_id = int(message_id_text[7:])

        description = description.replace("Описание: ", '')
        description = description.replace("Каменты: ", '')
        good = {
            "photo_link": photo_link,
            "description": description,
            "seller": seller,
            "photo": photo,
            "date": date,
            "message_id": message_id
        }
        # print(good)
        goods_list.append(good)

    json_filename = os.path.splitext(_filename)[0] + ".json"
    bot_util.save_json_file(json_filename, goods_list)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("give me directory of exported chat with message*.html")
        exit(-1)

    dir_name = sys.argv[1]

    html_files = glob.glob(os.path.join(dir_name, "messages*.html"))
    to_parse_files = html_files

    print(to_parse_files)

    for f in to_parse_files:
        process_html(f)

