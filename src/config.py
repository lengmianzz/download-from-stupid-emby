from pydantic import BaseModel


class Config(BaseModel):
    host: str
    user_name: str
    password: str
    user_id: str 
    api_key: str 
    