#!/usr/bin/env python3
"""
Точка входа для Railway с инициализацией базы данных
"""
import asyncio
import logging
import os
from aiohttp import web
from database import initialize_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_app_with_db():
    """Создает приложение с инициализацией базы данных"""
    # Инициализируем базу данных
    db_initialized = await initialize_database()
    if db_initialized:
        logger.info("Database initialized successfully")
    else:
        logger.warning("Database initialization failed, continuing without DB")
    
    # Импортируем после инициализации DB
    from app import create_app
    return create_app()

async def main():
    """Главная асинхронная функция"""
    port = int(os.environ.get('PORT', 8080))
    host = os.environ.get('HOST', '0.0.0.0')
    
    logger.info(f"Starting DailyBot on {host}:{port}")
    
    # Создаем приложение с инициализацией DB
    application = await create_app_with_db()
    
    # Запускаем сервер
    web.run_app(application, host=host, port=port)

if __name__ == '__main__':
    asyncio.run(main())
