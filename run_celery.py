from celery_project.tasks import get_goods_and_start_check_for_sold

if __name__ == '__main__':
    get_goods_and_start_check_for_sold.delay()


