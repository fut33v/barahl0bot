from celery.schedules import crontab

broker_url = 'redis://localhost'
timezone = 'Europe/Moscow'
enable_utc = True

beat_schedule = {
    'get_old_goods_and_mark_as_sold-every-day': {
        'task': 'celery_project.tasks.get_old_goods_and_mark_as_sold',
        'schedule': crontab(hour=16, minute=11),
        'args': ()
    },
    'get_goods_and_start_check_for_sold': {
        'task': 'celery_project.tasks.get_goods_and_start_check_for_sold',
        'schedule': crontab(hour=16, minute=30),
        'args': ()
    }

}

# task_serializer = 'json'
# result_serializer = 'json'
# accept_content = ['json']
