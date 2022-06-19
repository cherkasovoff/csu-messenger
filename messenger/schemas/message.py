from pydantic import BaseModel
import json

class Message(BaseModel):
    user_id: int
    chat_id: int
    text: str
    edited: bool
    read: bool

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)


class MessageInDB(Message):
    id: int

    class Config:
        orm_mode = True
