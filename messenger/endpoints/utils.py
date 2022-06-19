"""Различные методы проверки функционала"""
from datetime import datetime
from os import getenv
import pytz

from fastapi import APIRouter, WebSocket, Body
from fastapi.responses import HTMLResponse

from core.broker.celery import celery_app
from core.broker.redis import redis
from utils import async_query


router = APIRouter(prefix="/utils")


@router.post("/send_celery_task")
def send_celery_task(begin_datetime: datetime):
    """Запускает выполнение задачи queue.test
    
    Args:
        begin_datetime: datetime, когда запустить задачу
    """
    timezone = pytz.timezone(getenv("TZ"))
    dt_with_timezone = timezone.localize(begin_datetime)

    celery_app.send_task("queue.test", eta=dt_with_timezone)


html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body onLoad="loadPage(event)">
        <h1>WebSocket Chat</h1>
        <span id="status"></span>
        <form action="" onsubmit="authorize(event)">
            <input type="text" id="userLogin" autocomplete="off" placeholder="login"/>
            <input type="password" id="userPassword" autocomplete="off" placeholder="password"/>
            <input type="submit" value="Login">
            <input type="button" onClick="logout(event)" value="Log out">
        </form>
        <hr>
        <input type="button" onClick="loadAllMyChats(event)" value="Load my chats">
        <ul id='mychats'>
        </ul>
        <hr>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var global_chat_id = null;
            function loadPage(event) {
                 const TOKEN = localStorage.getItem("TOKEN")
                 if(TOKEN !== null) {
                    document.getElementById("status").innerHTML = `<font color='#00FF00'>Authorized as ${localStorage.getItem("USER_NAME")} (${localStorage.getItem("USER_LOGIN")})</font>`
                 }
                 else {
                    document.getElementById("status").innerHTML = "<font color='#FF0000'>Unauthorized</font>"
                 }
            }
            var ws = null;
            var TOKEN = null;
            const onmessagews = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            // ws.onmessage = onmessagews;
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                const json_request_body = JSON.stringify({
                    user_id: localStorage.getItem("USER_ID"),
                    chat_id: global_chat_id,
                    text: input.value,
                    edited: false,
                    read: false
                });
                console.log(json_request_body);
                fetch(`/message/`, {method: 'POST', headers: { Authorization: "Bearer " + TOKEN, "Content-Type": "application/json" }, body: json_request_body})
                input.value = ''
                event.preventDefault()
            }
            async function authorize(event) {
                event.preventDefault()
                const formData = new FormData();
                var login = document.getElementById("userLogin")
                formData.append('username', login.value);
                var password  = document.getElementById("userPassword")
                formData.append('password', password.value);
                await fetch('/login/', {method: 'POST', body: formData}).then(r => r.json())
                    .then(data => {
                        localStorage.setItem("TOKEN", data.access_token)
                        return data
                    })
                    .then(data => {
                        const TOKEN = localStorage.getItem("TOKEN")
                        fetch('/user/', {method: 'GET', headers: { Authorization: "Bearer " + TOKEN }}).then(r => r.json())
                            .then(data => {
                                localStorage.setItem("USER_ID", data.id)
                                localStorage.setItem("USER_NAME", data.name)
                                localStorage.setItem("USER_LOGIN", data.login)
                                return data
                            })
                            .then(data => {
                                loadPage(null)
                            })
                    })
                
            }
            function logout(event) {
                localStorage.removeItem("TOKEN")
                loadPage(null)
            }
            function loadAllMyChats(event) {
                event.preventDefault()
                const TOKEN = localStorage.getItem("TOKEN")
                if(TOKEN === "null") {
                    alert("Authenticate before")
                    return
                }
                var result = Array();
                fetch('/chat/my', {method: 'GET', headers: { Authorization: "Bearer " + TOKEN }}).then(r => r.json())
                    .then(data => data.forEach(element => { 
                        var mychats = document.getElementById('mychats')
                        var oneChat = document.createElement('li')
                        var button = document.createElement('button')
                        button.setAttribute("onClick", `connectToChat(${element.id})`);
                        var content = document.createTextNode(element.name)
                        button.appendChild(content)
                        oneChat.appendChild(button)
                        mychats.appendChild(oneChat)
                    }))
            }
            function connectToChat(chat_id) {
                ws?.close();
                ws = new WebSocket("ws://192.168.0.101:8080/utils/ws/" + chat_id);
                ws.onmessage = onmessagews;
                global_chat_id = chat_id;
            }
        </script>
    </body>
</html>
"""


@router.get("/ws-page")
async def ws_page():
    """html-страница с подключением к вебсокету"""
    return HTMLResponse(html)


@router.websocket("/ws/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: int):
    if chat_id is None:
        return

    await websocket.accept()
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"chat-{chat_id}")

    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True)

        if message:
            await websocket.send_text(message["data"].decode())


@router.get("/ws-pubsub")
async def ws_pubsub(user_id: int, text: str = "test text"):
    """Публикует событие в очередь пользователя"""
    await redis.publish(f"user-{user_id}", text)


@router.post("/post_process_message")
async def post_process_message(message: str = Body(..., embed=True)):
    """Пост-обработка сообщений: выделение ссылок, упоминаний и и.д."""
    url = "http://lanhost:8085/extra"
    extra = await async_query(task_url=url, text=message)

    return extra
