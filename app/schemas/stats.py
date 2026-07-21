from pydantic import BaseModel


class UserCountOut(BaseModel):
    user_count: int


class SwimCountOut(BaseModel):
    swim_count: int
