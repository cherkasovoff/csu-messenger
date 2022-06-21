import asyncio
import threading

from fastapi import APIRouter, Depends, HTTPException, status

from deps import get_db, get_current_user
import crud.message as crud
import crud.chat as chat_crud
from schemas.message import Message, MessageInDB, MessageWithDate, CreateMessageWithDate
from core.broker.redis import redis

import json

from utils import async_query

mutex = threading.Lock()

router = APIRouter(prefix="/message")


@router.get("/", response_model=MessageInDB)
async def get_message(message_id: int, user_id=Depends(get_current_user), db=Depends(get_db)):  # user_id=Depends(get_current_user)
    """Получить сообщение по заданному id"""
    message = crud.get_message_by_id(db=db, message_id=message_id)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return message


@router.get("/allMy", response_model=(MessageInDB))
async def get_all_messages(user_id=Depends(get_current_user), db=Depends(get_db)):
    """Получить все сообщения пользователя"""
    messages = crud.get_all_messages_by_user(db=db, user_id=user_id)
    if messages is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return messages


@router.get("/allInChat", response_model=MessageInDB)
async def get_all_messages(chat_id: int, user_id=Depends(get_current_user), db=Depends(get_db)):
    """Получить все сообщения пользователя"""
    messages = crud.get_all_messages_in_chat(db=db, chat_id=chat_id)
    if messages is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return messages


@router.post("/", response_model=MessageInDB)
async def create_message(message: Message, user_id=Depends(get_current_user), db=Depends(get_db)):
    """Отправить сообщение"""
    message.user_id = user_id
    mutex.acquire()
    message.text = await process_message(message.text)
    mutex.release()
    result = crud.create_message(db=db, message=message)
    await redis.publish(f"chat-{message.chat_id}", result.toJSON())
    return result


@router.post("/scheduled", response_model=MessageWithDate)
async def create_scheduled_message(message: CreateMessageWithDate, user_id=Depends(get_current_user), db=Depends(get_db)):
    """Отправить сообщение"""
    message.user_id = user_id
    mutex.acquire()
    message.text = await process_message(message.text)
    mutex.release()
    result = crud.create_sheduled_message(db=db, message=message)
    return result


@router.delete("/")
async def delete_message(message_id: int, user_id=Depends(get_current_user), db=Depends(get_db)):
    """Удалить сообщение"""
    message = crud.get_message_by_id(db=db, message_id=message_id)
    if str(message.user_id) != str(user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"{message.user_id} != {user_id}")
    await redis.publish(f"chat-{message.chat_id}", f"DELETE-{message.id}")
    crud.delete_message(db=db, message_id=message_id)


@router.put("/", response_model=MessageInDB)
async def edit_message(message: MessageInDB, user_id=Depends(get_current_user), db=Depends(get_db)):
    """Изменить сообщение"""
    if str(message.user_id) != str(user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    mutex.acquire()
    message.text = await process_message(message.text)
    mutex.release()
    message_db = crud.edit_message(db=db, message=message)
    await redis.publish(f"chat-{message.chat_id}", f"EDIT-{message.id}")
    return message_db


async def process_message(text: str):
    url = "http://lanhost:8085/extra"
    try:
        extra = await async_query(task_url=url, text=text)
    except BaseException as e:
        return text
    for one in extra:
        if one['type'] == 'link':
            link = one['text']
            if link.endswith('.jpg') or link.endswith('.png') or link.endswith('.gif'):
                text = text.replace(one['text'], f"<br><img src='{one['text']}'>")
            elif link.startswith('https://www.youtube.com/watch?v='):
                code = link.split('=')[1]
                text = text.replace(one['text'], f"<br><iframe width='560' height='315' src='https://www.youtube.com/embed/{code}' title='YouTube video player' frameborder='0' allow='accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture' allowfullscreen></iframe>")
            elif link.startswith('https://youtu.be/'):
                code = link.split('/')[-1]
                text = text.replace(one['text'], f"<br><iframe width='560' height='315' src='https://www.youtube.com/embed/{code}' title='YouTube video player' frameborder='0' allow='accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture' allowfullscreen></iframe>")
            elif link.startswith('https://music.yandex.ru/album/'):
                codes = link.split('/')
                track_id = codes[-1]
                album_id = codes[-3]
                text = text.replace(one['text'], f"<br><iframe frameborder='0' style='border:none;width:100%;height:90px;' width='100%' height='90' src='https://music.yandex.ru/iframe/#track/{track_id}/{album_id}'></iframe>")
            else:
                text = text.replace(one['text'], f"<a href='{one['text']}' target=\"_blank\">{one['text']}</a>")
        elif one['type'] == 'hashtag':
            text = text.replace(one['text'], f"<a href='https://www.google.com/search?q={one['text'][1:]}' target=\"_blank\">{one['text']}</a>")
        elif one['type'] == 'mention':
            text = text.replace(one['text'], f"<a href='https://t.me/{one['text'][1:]}' target=\"_blank\">{one['text']}</a>")
    return text

