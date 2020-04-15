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
        width = photo_size['width']
        if width > max_width:
            photo_url = photo_size['src']
            max_width = width
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

    def get_groups(self, group_ids):
        response = self._vk_api.groups.getById(group_ids=group_ids, fields='photo_200')
        groups = []
        for g in response:
            groups.append(Group(g))
        return groups

