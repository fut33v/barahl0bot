__author__ = 'fut33v'


def get_message(update):
    if not isinstance(update, dict):
        return None
    if "message" in update:
        return update['message']
    return None


def get_user_id(message):
    if not isinstance(message, dict):
        return None
    if 'from' in message:
        if 'id' in message['from']:
            return message['from']['id']
        return None


def get_chat_id(message):
    if not isinstance(message, dict):
        return None
    if 'chat' in message:
        chat = message['chat']
        if 'id' in chat:
            return chat['id']
    return None


def get_text(message):
    if not isinstance(message, dict):
        return None
    if 'text' in message:
        return message['text']
    return None
