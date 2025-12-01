from typing import Optional
from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """Модель для создания пользователя - соответствует API сервиса авторизации"""
    # УБИРАЕМ alias, используем snake_case как на сервере
    chat_id: int = Field(...)  # Сервер ожидает chat_id, а не chatId
    name: Optional[str] = None
    username: Optional[str] = None
    telegram_username: Optional[str] = None

    class Config:
        # Используем snake_case для всех полей
        populate_by_name = True
        # Опционально: можно указать, чтобы модель принимала и camelCase
        extra = "ignore"


class UserResponse(BaseModel):
    """Модель ответа сервиса авторизации"""
    id: int
    # Здесь тоже убираем alias, если сервер возвращает snake_case
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