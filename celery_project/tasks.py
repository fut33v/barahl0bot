from __future__ import absolute_import, unicode_literals
from .celery_app import app
from .tasks_logic import BarahlochTasksLogic

app.config_from_object('celeryconfig')


@app.task
def test(arg):
    print(arg)


@app.task
def get_goods_and_start_check_for_sold():
    goods = BarahlochTasksLogic.get_goods_show_ids(filter_days_down_limit=180, filter_days_up_limit=0)
    i = 0
    for g in goods:
        check_good_for_sold_and_mark_as_sold_if_so.apply_async((g[0], g[1]), countdown=i)
        i += 1


@app.task
def get_old_goods_and_mark_as_sold():
    goods = BarahlochTasksLogic.get_goods_show_ids(filter_days_down_limit=9999, filter_days_up_limit=180)
    for g in goods:
        mark_good_as_sold.delay(g[0], g[1])


@app.task
def check_good_for_sold_and_mark_as_sold_if_so(owner_id, photo_id):
    sold = BarahlochTasksLogic.check_is_sold(owner_id, photo_id)
    if sold:
        mark_good_as_sold.delay(owner_id, photo_id)


@app.task
def mark_good_as_sold(owner_id, photo_id):
    BarahlochTasksLogic.set_good_sold(owner_id, photo_id)


@app.task
def set_good_sold_in_telegram(owner_id, photo_id):
    return BarahlochTasksLogic.update_good_telegram(owner_id, photo_id)
