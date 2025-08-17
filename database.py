"""
Модели базы данных для астрологического бота
"""
import os
import logging
from datetime import datetime, date, time
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    create_engine, Column, Integer, BigInteger, String, Date, Time, Boolean,
    DateTime, Text, JSON, ForeignKey, Index
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.dialects.postgresql import POINT, JSONB
from sqlalchemy.sql import func

logger = logging.getLogger(__name__)

# Конфигурация базы данных
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    # Railway использует postgres://, но SQLAlchemy 2.0 требует postgresql://
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# Базовый класс для всех моделей
Base = declarative_base()

class User(Base):
    """Модель пользователя"""
    __tablename__ = 'users'
    
    # Первичный ключ
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Telegram данные
    telegram_user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    telegram_username = Column(String(255))
    telegram_first_name = Column(String(255))
    telegram_last_name = Column(String(255))
    
    # Персональные данные
    name = Column(String(255), nullable=False)
    birth_date = Column(Date, nullable=False)
    birth_time = Column(Time, nullable=False)
    birth_time_unknown = Column(Boolean, default=False)
    birth_place = Column(String(500), nullable=False)
    birth_coordinates = Column(POINT)
    
    # Текущее местоположение
    current_location = Column(String(500))
    current_coordinates = Column(POINT)
    current_timezone = Column(String(50))
    
    # Настройки прогнозов
    forecast_time = Column(Time, nullable=False, default=time(9, 0))
    forecast_frequency = Column(String(20), default='daily')
    language = Column(String(10), default='ru')
    astro_level = Column(String(20), default='beginner')
    
    # Статус регистрации
    registration_step = Column(String(50), default='not_started')
    registration_complete = Column(Boolean, default=False)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_active = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи с другими таблицами
    forecasts = relationship("UserForecast", back_populates="user", cascade="all, delete-orphan")
    activities = relationship("UserActivity", back_populates="user", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь для совместимости с существующим кодом"""
        return {
            'user_id': self.telegram_user_id,
            'personal': {
                'name': self.name,
                'birth_date': self.birth_date.isoformat() if self.birth_date else None,
                'birth_time': self.birth_time.strftime('%H:%M') if self.birth_time else None,
                'birth_time_unknown': self.birth_time_unknown,
                'birth_place': self.birth_place,
                'birth_coordinates': self.birth_coordinates
            },
            'current': {
                'location': self.current_location,
                'coordinates': self.current_coordinates,
                'timezone': self.current_timezone
            },
            'preferences': {
                'forecast_time': self.forecast_time.strftime('%H:%M') if self.forecast_time else None,
                'frequency': self.forecast_frequency,
                'language': self.language,
                'astro_level': self.astro_level
            },
            'metadata': {
                'registration_step': self.registration_step,
                'registration_complete': self.registration_complete,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'last_active': self.last_active.isoformat() if self.last_active else None
            }
        }
    
    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_user_id}, name='{self.name}')>"

class UserForecast(Base):
    """Модель прогнозов пользователя"""
    __tablename__ = 'user_forecasts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    forecast_date = Column(Date, nullable=False)
    forecast_type = Column(String(50), nullable=False)  # 'daily', 'weekly', 'monthly'
    content = Column(JSONB, nullable=False)  # Полный прогноз
    astronomical_data = Column(JSONB)  # Астрономические данные
    
    sent_at = Column(DateTime(timezone=True))
    read_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    user = relationship("User", back_populates="forecasts")
    
    def __repr__(self):
        return f"<UserForecast(id={self.id}, user_id={self.user_id}, date={self.forecast_date})>"

class AstronomicalCache(Base):
    """Кэш астрономических данных"""
    __tablename__ = 'astronomical_cache'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cache_key = Column(String(255), unique=True, nullable=False, index=True)
    location = Column(String(255))
    coordinates = Column(POINT)
    data = Column(JSONB, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<AstronomicalCache(key='{self.cache_key}', expires={self.expires_at})>"

class UserActivity(Base):
    """Логи активности пользователей"""
    __tablename__ = 'user_activities'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    activity_type = Column(String(50), nullable=False)  # 'command', 'registration_step', 'forecast_request'
    activity_data = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Связи
    user = relationship("User", back_populates="activities")
    
    def __repr__(self):
        return f"<UserActivity(id={self.id}, user_id={self.user_id}, type='{self.activity_type}')>"

# Дополнительные индексы
Index('idx_users_coordinates', User.current_coordinates, postgresql_using='gist')
Index('idx_users_forecast_active', User.forecast_time, postgresql_where=User.registration_complete.is_(True))
Index('idx_forecasts_user_date', UserForecast.user_id, UserForecast.forecast_date)
Index('idx_forecasts_sent', UserForecast.sent_at, postgresql_where=UserForecast.sent_at.isnot(None))
Index('idx_cache_coordinates', AstronomicalCache.coordinates, postgresql_using='gist')

class DatabaseManager:
    """Менеджер для работы с базой данных"""
    
    def __init__(self):
        self.engine = None
        self.async_session_factory = None
        self.sync_session_factory = None
    
    async def initialize(self):
        """Инициализация подключения к базе данных"""
        if not DATABASE_URL:
            logger.error("DATABASE_URL not configured")
            return False
        
        try:
            # Создаем асинхронный движок
            self.engine = create_async_engine(
                DATABASE_URL,
                echo=False,  # Установите True для отладки SQL запросов
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600
            )
            
            # Создаем фабрику сессий
            self.async_session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            logger.info("Database connection initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            return False
    
    async def create_tables(self):
        """Создание таблиц (для разработки, в продакшене используйте миграции)"""
        if not self.engine:
            raise RuntimeError("Database not initialized")
        
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise
    
    async def get_session(self) -> AsyncSession:
        """Получить сессию базы данных"""
        if not self.async_session_factory:
            raise RuntimeError("Database not initialized")
        return self.async_session_factory()
    
    async def close(self):
        """Закрыть соединение с базой данных"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")

# Глобальный экземпляр менеджера базы данных
db_manager = DatabaseManager()

async def get_user_by_telegram_id(telegram_user_id: int) -> Optional[User]:
    """Получить пользователя по Telegram ID"""
    async with db_manager.get_session() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )
        return result.scalar_one_or_none()

async def create_or_update_user(user_data: Dict[str, Any]) -> User:
    """Создать или обновить пользователя"""
    async with db_manager.get_session() as session:
        from sqlalchemy import select
        
        telegram_user_id = user_data['user_id']
        
        # Попробуем найти существующего пользователя
        result = await session.execute(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Обновляем существующего пользователя
            for key, value in user_data.get('personal', {}).items():
                if key == 'birth_date' and isinstance(value, str):
                    setattr(user, key, datetime.strptime(value, '%Y-%m-%d').date())
                elif key == 'birth_time' and isinstance(value, str):
                    setattr(user, key, datetime.strptime(value, '%H:%M').time())
                else:
                    setattr(user, key, value)
            
            for key, value in user_data.get('current', {}).items():
                setattr(user, f'current_{key}', value)
            
            for key, value in user_data.get('preferences', {}).items():
                if key == 'forecast_time' and isinstance(value, str):
                    setattr(user, key, datetime.strptime(value, '%H:%M').time())
                else:
                    setattr(user, key, value)
            
            for key, value in user_data.get('metadata', {}).items():
                setattr(user, key, value)
            
            user.updated_at = datetime.utcnow()
        else:
            # Создаем нового пользователя
            personal = user_data.get('personal', {})
            current = user_data.get('current', {})
            preferences = user_data.get('preferences', {})
            metadata = user_data.get('metadata', {})
            
            user = User(
                telegram_user_id=telegram_user_id,
                telegram_username=user_data.get('telegram_username'),
                telegram_first_name=user_data.get('telegram_first_name'),
                telegram_last_name=user_data.get('telegram_last_name'),
                
                name=personal.get('name', ''),
                birth_date=datetime.strptime(personal['birth_date'], '%Y-%m-%d').date() if personal.get('birth_date') else None,
                birth_time=datetime.strptime(personal['birth_time'], '%H:%M').time() if personal.get('birth_time') else None,
                birth_time_unknown=personal.get('birth_time_unknown', False),
                birth_place=personal.get('birth_place', ''),
                
                current_location=current.get('location'),
                current_coordinates=current.get('coordinates'),
                current_timezone=current.get('timezone'),
                
                forecast_time=datetime.strptime(preferences['forecast_time'], '%H:%M').time() if preferences.get('forecast_time') else time(9, 0),
                forecast_frequency=preferences.get('frequency', 'daily'),
                language=preferences.get('language', 'ru'),
                astro_level=preferences.get('astro_level', 'beginner'),
                
                registration_step=metadata.get('registration_step', 'not_started'),
                registration_complete=metadata.get('registration_complete', False)
            )
            session.add(user)
        
        await session.commit()
        await session.refresh(user)
        return user

async def log_user_activity(telegram_user_id: int, activity_type: str, activity_data: Optional[Dict] = None):
    """Логирование активности пользователя"""
    try:
        user = await get_user_by_telegram_id(telegram_user_id)
        if not user:
            return
        
        async with db_manager.get_session() as session:
            activity = UserActivity(
                user_id=user.id,
                activity_type=activity_type,
                activity_data=activity_data
            )
            session.add(activity)
            await session.commit()
            
    except Exception as e:
        logger.error(f"Error logging user activity: {e}")

# Функция для инициализации базы данных при старте приложения
async def initialize_database():
    """Инициализация базы данных"""
    success = await db_manager.initialize()
    if success:
        # В разработке создаем таблицы автоматически
        # В продакшене используйте миграции Alembic
        if os.getenv('ENVIRONMENT') != 'production':
            await db_manager.create_tables()
    return success
