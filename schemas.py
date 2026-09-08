from pydantic import BaseModel

class UserCreate(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class FavoriteCityCreate(BaseModel):
    city_name: str

class FavoriteCityResponse(BaseModel):
    id: int
    city_name: str

    class Config:
        from_attributes = True

