from __future__ import absolute_import, unicode_literals
from celery import Celery
from .tasks_logic import BarahlochTasksLogic

app = Celery('celery_project', broker='redis://localhost', include=['celery_project.tasks'])

BarahlochTasksLogic.init('settings.json')

if __name__ == '__main__':
    app.start()
