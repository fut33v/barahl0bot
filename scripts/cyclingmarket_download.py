from python_telegram_settings import API_ID, API_HASH, DATABASE_ENCRYPTION_KEY, PHONE

from telegram.client import Telegram
import os
import util
import datetime


DATA_DIR = 'data/'
SINGLE_DIR = 'data/single/'
ALBUMS_DIR = 'data/albums/'
PROCESSED_DIR = 'data/processed/'


def create_dir(dir_path):
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)


create_dir(DATA_DIR)
create_dir(ALBUMS_DIR)
create_dir(SINGLE_DIR)
create_dir(PROCESSED_DIR)


def download_full_history():

    next_message_id = 0
    while True:
        r = tg.call_method('getChatHistory',
                           params={'chat_id': chat_id,
                                   'from_message_id': next_message_id,
                                   'offset': 0,
                                   'limit': 100,
                                   'only_local': False,
                                   })
        r.wait()
        update = r.update
        if 'messages' not in update:
            print('no messages in update')
            break

        for message in update['messages']:
            media_album_id = message['media_album_id']
            if int(media_album_id) == 0:
                util.save_json_file('{}/{}.json'.format(SINGLE_DIR, message['id']), message)
            else:
                album_dir = ALBUMS_DIR + media_album_id
                if not os.path.exists(album_dir):
                    os.mkdir(album_dir)
                util.save_json_file('{}/{}/{}.json'.format(ALBUMS_DIR, media_album_id, message['id']), message)
            text = message.get('text', None)
            date = message['date']
            timestamp = datetime.datetime.fromtimestamp(date)
            print(timestamp.strftime('%Y-%m-%d %H:%M:%S'))
        if len(update['messages']) == 0:
            break
        next_message_id = update['messages'][-1]['id']


def update_url_id(message_file_name, directory):
    message_id = message_file_name.split('.')[0]
    print(message_id)
    r = tg.call_method('getMessageLink', params={'chat_id': chat_id, 'message_id': message_id})
    r.wait()
    if not r.update:
        return
    if 'url' not in r.update:
        return
    url_id = r.update['url'].split('/')[-1]
    print('https://t.me/cyclingmarket/{}'.format(url_id))
    full_path = os.path.join(directory, message_file_name)
    data = util.load_json_file(full_path)
    data['url_id'] = url_id
    util.save_json_file(full_path, data)


def get_from_text(text, entity):
    length = entity['length']
    offset = entity['offset']
    return text[offset:offset+length]


def get_city_from_text(text, price_ent, seller_ent):
    offset = price_ent['offset'] + price_ent['length']
    return text[offset:seller_ent['offset']]


def process_singles():
    singles = os.listdir(SINGLE_DIR)
    for fname in singles:
        fname = SINGLE_DIR + fname
        data = util.load_json_file(fname)

        if 'content' not in data:
            continue
        if 'caption' not in data['content']:
            continue

        content = data['content']
        caption = content['caption']
        text = caption['text']

        prod_caption_ent = None
        prod_price_ent = None
        prod_seller_ent = None
        prod_descr_ent = None
        hashtag_ents = []
        entities = caption['entities']
        for e in entities:
            entity_type = e['type']['@type']
            if entity_type == 'textEntityTypeHashtag':
                hashtag_ents.append(e)
            if entity_type == 'textEntityTypeBold':
                if not prod_caption_ent:
                    prod_caption_ent = e
                else:
                    prod_price_ent = e
            if entity_type == 'textEntityTypeItalic':
                prod_descr_ent = e
            if entity_type == 'textEntityTypeMentionName':
                prod_seller_ent = e

        if prod_caption_ent is None or prod_price_ent is None or prod_seller_ent is None or prod_descr_ent is None:
            continue

        product_hashtags = []
        for h in hashtag_ents:
            product_hashtags.append(get_from_text(text, h))
        product_caption = get_from_text(text, prod_caption_ent)
        product_descr = get_from_text(text, prod_descr_ent)
        product_price = get_from_text(text, prod_price_ent)
        product_seller_name = get_from_text(text, prod_seller_ent)
        product_city = get_city_from_text(text, prod_price_ent, prod_seller_ent)

        product_seller_id = prod_seller_ent['type']['user_id']

        photo_file_id = content['photo']['sizes'][-1]['photo']['remote']['id']

        r = tg.call_method('getUser', params={'user_id': product_seller_id})
        r.wait()
        seller = r.update

        product = {
            'hashtags': product_hashtags,
            'caption': product_caption,
            'descr': product_descr,
            'price': product_price,
            'city': product_city,
            'seller': {
                'id': product_seller_id,
                'full_name': product_seller_name,
                'username': seller['username'],
                'first_name': seller['first_name'],
                'last_name': seller['last_name'],
                'profile_photo': seller.get('profile_photo', None),
            },
            'photo': photo_file_id,
            'date': data['date']
        }

        url_id = data['url_id']
        pr_dir = os.path.join(PROCESSED_DIR, url_id)
        create_dir(pr_dir)

        util.save_json_file(os.path.join(pr_dir, 'data.json'), product)

        print(product)


if __name__ == '__main__':
    tg = Telegram(
        api_id=API_ID,
        api_hash=API_HASH,
        phone=PHONE,
        database_encryption_key=DATABASE_ENCRYPTION_KEY,
    )

    tg.login()

    DOWNLOAD = False

    result = tg.call_method('searchPublicChat', params={'username': 'cyclingmarket'})
    result.wait()

    if 'id' in result.update:
        chat_id = result.update['id']

    if DOWNLOAD:
        download_full_history()

        single_photo_messages = os.listdir(SINGLE_DIR)
        for fn in single_photo_messages:
            update_url_id(fn, SINGLE_DIR)

        albums_dirs = os.listdir(ALBUMS_DIR)
        for album_dir in albums_dirs:
            full_album_dir_path = ALBUMS_DIR + album_dir
            album_files = os.listdir(full_album_dir_path)
            for af in album_files:
                update_url_id(af, full_album_dir_path)

    process_singles()

    tg.stop()

