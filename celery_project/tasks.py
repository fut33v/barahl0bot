from __future__ import absolute_import, unicode_literals
from .celery_app import app
from .tasks_logic import BarahlochTasksLogic


@app.task
def add(x, y):
    return x + y


@app.task
def get_goods_and_start_check_for_sold():
    goods = BarahlochTasksLogic.get_goods_show_ids()
    goods = goods
    i = 0
    for g in goods:
        process_good.apply_async((g[0], g[1]), countdown=i)
        i += 1


@app.task
def process_good(owner_id, photo_id):
    sold = BarahlochTasksLogic.check_is_sold(owner_id, photo_id)
    if sold:
        BarahlochTasksLogic.set_good_sold(owner_id, photo_id)
        # set_good_sold_in_telegram.delay(owner_id, photo_id)


@app.task
def set_good_sold_in_telegram(owner_id, photo_id):
    return BarahlochTasksLogic.update_good_telegram(owner_id, photo_id)
