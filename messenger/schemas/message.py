from pydantic import BaseModel


class Message(BaseModel):
    user_id: int
    chat_id: int
    text: str
    edited: bool
    read: bool


class MessageInDB(Message):
    id: int

    class Config:
        orm_mode = True
