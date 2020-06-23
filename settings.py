import util

COMMENTS_STRING_RESTRICTION = 600
DESCRIPTION_STRING_RESTRICTION = 600
DESCRIPTION_PLUS_COMMENTS_STRING_RESTRICTION = 700


class Barahl0botSettings:
    def __init__(self, _filename):
        self._settings = util.load_json_file(_filename)
        print(self._settings)

        self.dbms = self._settings['dbms']
        self.bot_name = self._settings['bot_name']

        self.storage_vk = self._get_setting('storage_vk')

        self.token_telegram = self._settings['token_telegram']
        self.token_vk = self._settings['token_vk']

        self.admins = set(self._settings['admins'])
        self.channel = self._settings['channel']

        self.website = self._settings['website']

        self.error_channel = self._get_setting('error_channel')

        self.seconds_to_sleep = 90
        self.timeout_for_photo_seconds = 180
        self.too_old_for_photo_seconds = 24 * 60 * 60
        self.seconds_to_sleep_between_albums = 1
        self.seconds_to_sleep_limit_reached = 60 * 60 * 2
        self.days_timeout_for_product = 7

        seconds_to_sleep = self._settings['seconds_to_sleep']
        if seconds_to_sleep:
            self.seconds_to_sleep = seconds_to_sleep
        timeout_for_photo_seconds = self._get_setting('timeout_for_photo_seconds')
        if timeout_for_photo_seconds:
            self.timeout_for_photo_seconds = timeout_for_photo_seconds
        too_old_for_photo_seconds = self._get_setting('too_old_for_photo_seconds')
        if too_old_for_photo_seconds:
            self.too_old_for_photo_seconds = too_old_for_photo_seconds
        seconds_to_sleep_between_albums = self._get_setting('seconds_to_sleep_between_albums')
        if seconds_to_sleep_between_albums:
            self.seconds_to_sleep_between_albums = seconds_to_sleep_between_albums
        seconds_to_sleep_limit_reached = self._get_setting('seconds_to_sleep_limit_reached')
        if seconds_to_sleep_limit_reached:
            self.seconds_to_sleep_limit_reached = seconds_to_sleep_limit_reached
        days_timeout_for_product = self._settings.get('days_timeout_for_product', None)
        if days_timeout_for_product:
            self.days_timeout_for_product = days_timeout_for_product

    def _get_setting(self, name_string):
        if name_string in self._settings:
            return self._settings[name_string]
        return None


