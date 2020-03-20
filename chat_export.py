from bs4 import BeautifulSoup, NavigableString, Tag
import re
import os
import glob

from util import bot_util


def process_html(_filename):
    html_doc = open(_filename, 'r').read()
    soup = BeautifulSoup(html_doc, 'html.parser')

    photo_link_regexp = re.compile("jpg")
    seller_regexp = re.compile("Продавец")
    photo_regexp = re.compile("Фото")
    descr_regexp = re.compile("Описание")
    comments_regexp = re.compile("Каменты")

    goods_list = []
    messages = soup.find_all("div", class_="message default clearfix")
    for m in messages:
        messages_text = m.find_all("div", class_="text")
        for mt in messages_text:

            without_br = [x for x in mt.contents if x.name != 'br']

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

            if not seller:
                print(_filename, without_br, "\n\n")
            else:
                description = description.replace("Описание: ", '')
                description = description.replace("Каменты: ", '')
                good = {
                    "photo_link": photo_link,
                    "description": description,
                    "seller": seller,
                    "photo": photo
                }
                # print(good)
                goods_list.append(good)

    # json write
    json_filename = _filename.split(".")[0] + ".json"
    bot_util.save_json_file(json_filename, goods_list)


if __name__ == "__main__":
    dir_name = "chat_export/"
    html_files = glob.glob(dir_name + "*.html")
    # print(html_files)

    to_parse_files = []
    for i in range(8, 34):
        f = dir_name + "messages" + str(i) + ".html"
        if os.path.exists(f):
            to_parse_files.append(f)

    # to_parse_files = ["chat_export/messages8.html"]

    print(to_parse_files)
    for f in to_parse_files:
        process_html(f)

