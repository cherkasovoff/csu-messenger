from pydantic import BaseModel
import json


class Message(BaseModel):
    user_id: int
    chat_id: int
    text: str

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)


class MessageInDB(Message):
    id: int
    edited: bool
    read: bool

    class Config:
        orm_mode = True


class MessageWithDate(MessageInDB):
    created_date: str
    maybesent: bool


class CreateMessageWithDate(Message):
    created_date: str
