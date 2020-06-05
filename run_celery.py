import sys

from celery_project.tasks import get_goods_and_start_check_for_sold
from celery_project import tasks_logic

# from vkontakte import VkontakteInfoGetter
# from settings import Barahl0botSettings


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("settings json file required")
        exit(-1)
    # tasks_logic.init(sys.argv[1])
    # check_for_sold.delay(-10698066, 457330194)
    get_goods_and_start_check_for_sold.delay()

