"""
Модели базы данных для DailyBot
"""
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, DateTime, Boolean, JSON, Float, ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
import logging

logger = logging.getLogger(__name__)

# База для всех моделей
class Base(DeclarativeBase):
    pass

# Энамы
class RegistrationStep(Enum):
    """Этапы регистрации пользователя"""
    NOT_STARTED = "not_started"
    NAME = "name"
    BIRTH_DATE = "birth_date"
    BIRTH_TIME = "birth_time"
    BIRTH_PLACE = "birth_place"
    CURRENT_LOCATION = "current_location"
    FORECAST_TIME = "forecast_time"
    COMPLETED = "completed"

class ActionType(Enum):
    """Типы действий пользователей"""
    REGISTRATION_STARTED = "registration_started"
    REGISTRATION_COMPLETED = "registration_completed"
    ASTRO_REQUEST = "astro_request"
    MOON_REQUEST = "moon_request"
    PROFILE_VIEW = "profile_view"
    HELP_REQUEST = "help_request"
    MESSAGE_SENT = "message_sent"
    LOCATION_SHARED = "location_shared"
    COMMAND_USED = "command_used"

# Модели
class User(Base):
    """Модель пользователя"""
    __tablename__ = 'users'
    
    # Основные поля
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    telegram_user_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    
    # Персональные данные
    name: Mapped[Optional[str]] = mapped_column(String(100))
    birth_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    birth_time: Mapped[Optional[str]] = mapped_column(String(5))  # HH:MM
    birth_time_unknown: Mapped[bool] = mapped_column(Boolean, default=False)
    birth_place: Mapped[Optional[str]] = mapped_column(String(200))
    
    # Текущее местоположение
    current_location: Mapped[Optional[str]] = mapped_column(String(200))
    current_coordinates: Mapped[Optional[Dict[str, float]]] = mapped_column(JSONB)  # {"lat": float, "lon": float}
    location_type: Mapped[Optional[str]] = mapped_column(String(20))  # "city" или "coordinates"
    
    # Настройки
    forecast_time: Mapped[Optional[str]] = mapped_column(String(5))  # HH:MM
    language: Mapped[str] = mapped_column(String(5), default="ru")
    astro_level: Mapped[str] = mapped_column(String(20), default="beginner")
    frequency: Mapped[str] = mapped_column(String(20), default="daily")
    
    # Telegram данные
    telegram_username: Mapped[Optional[str]] = mapped_column(String(100))
    telegram_first_name: Mapped[Optional[str]] = mapped_column(String(100))
    telegram_last_name: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Статус регистрации
    registration_step: Mapped[str] = mapped_column(String(50), default=RegistrationStep.NOT_STARTED.value)
    registration_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Метаданные
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    registered_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_activity: Mapped[Optional[datetime]] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Дополнительные данные
    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)
    
    # Связи
    actions: Mapped[List["UserAction"]] = relationship("UserAction", back_populates="user", cascade="all, delete-orphan")
    analytics: Mapped[List["UserAnalytics"]] = relationship("UserAnalytics", back_populates="user", cascade="all, delete-orphan")

class UserAction(Base):
    """Модель действий пользователя"""
    __tablename__ = 'user_actions'
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey('users.id'), nullable=False, index=True)
    
    # Данные действия
    action_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    command: Mapped[Optional[str]] = mapped_column(String(100))  # Для команд бота
    message_text: Mapped[Optional[str]] = mapped_column(Text)  # Текст сообщения
    
    # Контекст
    context: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)  # Дополнительные данные
    
    # Время
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    
    # Связи
    user: Mapped["User"] = relationship("User", back_populates="actions")

class UserAnalytics(Base):
    """Модель аналитики пользователя"""
    __tablename__ = 'user_analytics'
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey('users.id'), nullable=False, index=True)
    
    # Период аналитики
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)  # Дата (только дата, без времени)
    
    # Счетчики активности
    total_messages: Mapped[int] = mapped_column(Integer, default=0)
    total_commands: Mapped[int] = mapped_column(Integer, default=0)
    astro_requests: Mapped[int] = mapped_column(Integer, default=0)
    moon_requests: Mapped[int] = mapped_column(Integer, default=0)
    
    # Временные метрики
    first_activity_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_activity_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    session_duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    
    # Дополнительные данные
    commands_used: Mapped[Optional[List[str]]] = mapped_column(JSONB, default=list)  # Список использованных команд
    engagement_score: Mapped[float] = mapped_column(Float, default=0.0)  # Оценка вовлеченности
    
    # Связи
    user: Mapped["User"] = relationship("User", back_populates="analytics")

# Настройка подключения к БД
class DatabaseManager:
    """Менеджер базы данных"""
    
    def __init__(self):
        self.engine = None
        self.async_session = None
        self._initialized = False
    
    async def initialize(self):
        """Инициализация подключения к БД"""
        if self._initialized:
            return
        
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL not found in environment variables")
        
        # Конвертируем URL для asyncpg если нужно
        if database_url.startswith('postgresql://'):
            database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        elif not database_url.startswith('postgresql+asyncpg://'):
            database_url = 'postgresql+asyncpg://' + database_url
        
        self.engine = create_async_engine(
            database_url,
            echo=False,  # Логирование SQL запросов
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        logger.info("Database connection initialized")
        self._initialized = True
    
    async def create_tables(self):
        """Создание таблиц в БД"""
        if not self._initialized:
            await self.initialize()
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables created")
    
    async def get_session(self) -> AsyncSession:
        """Получить сессию БД"""
        if not self._initialized:
            await self.initialize()
        
        return self.async_session()
    
    async def close(self):
        """Закрыть подключение к БД"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")

# Глобальный менеджер БД
db_manager = DatabaseManager()

# Функции для работы с БД
async def init_database():
    """Инициализация БД при запуске приложения"""
    try:
        await db_manager.initialize()
        await db_manager.create_tables()
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

async def get_db_session() -> AsyncSession:
    """Получить сессию БД"""
    return await db_manager.get_session()

async def close_database():
    """Закрыть подключение к БД"""
    await db_manager.close()
