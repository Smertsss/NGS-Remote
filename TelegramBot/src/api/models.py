from typing import Optional
from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """Модель для создания пользователя - соответствует API сервиса авторизации"""
    chat_id: int = Field(...)
    name: Optional[str] = None
    username: Optional[str] = None
    telegram_username: Optional[str] = None

    class Config:
        populate_by_name = True
        extra = "ignore"


class UserResponse(BaseModel):
    """Модель ответа сервиса авторизации"""
    id: int
    chat_id: int = Field(...)
    name: Optional[str] = None
    username: Optional[str] = None
    telegram_username: Optional[str] = None
    is_deleted: bool = Field(default=False)

    class Config:
        from_attributes = True
        populate_by_name = True


class ErrorResponse(BaseModel):
    """Модель для ошибок API"""
    detail: str