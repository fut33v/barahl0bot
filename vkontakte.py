import vk_api
from enum import IntEnum
from structures import Seller, Group


class VkErrorCodesEnum(IntEnum):
    #: Достигнут количественный лимит на вызов метода
    LIMIT_REACHED = 29


def _get_widest_album_cover_photo_url(photo_sizes):
    photo_url = None
    max_width = 0
    for photo_size in photo_sizes:
        # type = photo_size['type']
        width = photo_size['width']
        if width > max_width:
            photo_url = photo_size['src']
            max_width = width
        if width == 0:
            photo_url = photo_size['src']
    return photo_url


class VkontakteInfoGetter:
    def __init__(self, token):
        self._vk_session = vk_api.VkApi(token=token)
        self._vk_api = self._vk_session.get_api()

    def get_photos_x(self, album):
        return self._vk_session.method(
            "execute.getPhotosX", values={'album_id': album.album_id, 'owner_id': album.owner_id}, raw=True)

    def update_album_info(self, album):
        if not album.owner_id or not album.album_id:
            return None

        album_info = self._vk_api.photos.getAlbums(owner_id=album.owner_id,
                                                   album_ids=album.album_id,
                                                   need_covers=1,
                                                   photo_sizes=1)
        if 'items' not in album_info:
            return None

        album_info = album_info['items'][0]

        album.title = album_info["title"]
        album.description = album_info["description"]
        album.photo = _get_widest_album_cover_photo_url(album_info["sizes"])

    def get_seller(self, seller_id):
        seller_info = self._vk_api.users.get(user_ids=seller_id, fields='city,photo_200')[0]
        return Seller(seller_info)

    def get_sellers(self, seller_ids):
        sellers = []
        number_of_thousands = int(len(seller_ids) / 1000) + 1
        for i in range(number_of_thousands):
            x = seller_ids[i * 1000:i * 1000 + 1000]
            response = self._vk_api.users.get(user_ids=x, fields='city,photo_200')[0]
            for s in response:
                sellers.append(Seller(s))
        return sellers

    def get_group(self, group_id):
        response = self._vk_api.groups.getById(group_ids=group_id, fields='photo_200')
        return Group(response)

    def get_groups(self, group_ids):
        groups = []
        number_of_thousands = int(len(group_ids) / 1000) + 1
        for i in range(number_of_thousands):
            x = group_ids[i * 1000:i * 1000 + 1000]
            x = [abs(y) for y in x]
            response = self._vk_api.groups.getById(group_ids=x, fields='photo_200')
            for g in response:
                groups.append(Group(g))
        return groups

    def get_cities(self, city_ids):
        cities = []
        number_of_thousands = int(len(city_ids) / 1000) + 1
        for i in range(number_of_thousands):
            x = city_ids[i * 1000:i * 1000 + 1000]
            c = self._vk_api.database.getCitiesById(city_ids=x)
            cities.extend(c)
        return cities

