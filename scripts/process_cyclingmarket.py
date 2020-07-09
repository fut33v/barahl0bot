import os
from cyclingmarket_download import PROCESSED_DIR
import util


def clear_city_string(s):
    s = s.replace('\n', '')
    s = s.replace(' ', '')
    s = s.lower()
    s = s.split('/')[0]
    s = s.split(',')[0]
    return s


SPB = ['с-пб', 'питер', 'санкт-петербург(доставказавашсчёт)',
       'спбплощадьвосстания', 'санк-петербург',
       'санкт-петербургдоставкакомпаниейсдэкзавашсчетпороссиииснг',
       'санктпетербург', 'спб', 'spb', 'петербург', 'санкт-петербург',
       'веледетвспбсдэком(пересылвмскзавашсчет)ценазастоковуюкомплектациюгайз', 'санкт-петербург+почта']

MOSCOW = ['москва-красногорск', 'москва', 'мск']

if __name__ == "__main__":
    processed = os.listdir(PROCESSED_DIR)
    cities = set()
    for post_id in processed:
        filename = os.path.join(PROCESSED_DIR, post_id, 'data.json')
        json = util.load_json_file(filename)
        if isinstance(json['city'], dict):
            continue
        city_clear = clear_city_string(json['city'])
        cities.add(city_clear)

        if city_clear in SPB:
            json['city'] = {'id': 2, 'text': json['city']}
        if city_clear in MOSCOW:
            json['city'] = {'id': 1, 'text': json['city']}
        if city_clear == 'ростов-на-дону':
            json['city'] = {'id': 119, 'text': json['city']}
        if city_clear == 'великийновгород':
            json['city'] = {'id': 35, 'text': json['city']}
        if city_clear == 'вологда':
            json['city'] = {'id': 41, 'text': json['city']}
        if city_clear == 'минск':
            json['city'] = {'id': 282, 'text': json['city']}
        if city_clear == 'уфа':
            json['city'] = {'id': 151, 'text': json['city']}
        if city_clear == 'казань':
            json['city'] = {'id': 60, 'text': json['city']}
        if city_clear == 'пенза':
            json['city'] = {'id': 109, 'text': json['city']}
        if city_clear == 'краснодар':
            json['city'] = {'id': 72, 'text': json['city']}

        util.save_json_file(filename, json)

    for c in cities:
        print(c)

