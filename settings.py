from util import bot_util


class Barahl0botSettings:
    def __init__(self, _filename):
        self._settings = bot_util.load_json_file(_filename)
        self.token_telegram = self._settings['token_telegram']
        self.token_vk = self._settings['token_vk']

        self.admins = set(self._settings['admins'])
        self.channel = self._settings['channel']

        self.seconds_to_sleep = self._settings['seconds_to_sleep']
        self.error_channel = self._get_optional_setting('error_channel')
        self.timeout_for_photo_seconds = self._get_optional_setting('timeout_for_photo_seconds')
        self.too_old_for_photo_seconds = self._get_optional_setting('too_old_for_photo_seconds')
        self.last_items_count = self._get_optional_setting('last_items_count')

    def _get_optional_setting(self, _name_string):
        if _name_string in self._settings:
            return self._settings[_name_string]
        return None


