from datetime import datetime
import time
from typing import List

from core.broker.celery import celery_app
from deps import get_db
import schemas.message as schema
from core.broker.redis import redis
import crud.message as crud
import asyncio
from celery import shared_task

celery_app.conf.beat_schedule = {
    'every-15-seconds': {
        'task': 'schedule_dispatcher',
        'schedule': 15,
    }
}

celery_app.autodiscover_tasks()


@celery_app.task(name="queue.test")
def test():
    print(datetime.now())


@shared_task(name="schedule_dispatcher")
def schedule_dispatcher():
    db = next(get_db())
    asyncio.run(check_nearest_messages(db))


async def check_nearest_messages(db):
    # while True:
    messages: List[schema.MessageWithDate] = crud.get_nearest_messages(db)
    await redis.publish(f'thread', f'Tried to receive scheduled messages {messages}')
    for message in messages:
        message_date = datetime.strptime(message.created_date, "%Y-%m-%d %H:%M:%S")
        current_date = datetime.now()
        delta = message_date - current_date
        minutes = delta.seconds / 60
        await redis.publish(f'thread', minutes)
        await redis.publish(f'thread', message.toJSON())
        if minutes < 1:
            crud.make_message_sendable(db=db, message=message)
            await redis.publish(f'chat-{message.chat_id}', message.toJSON())
        # time.sleep(30)
