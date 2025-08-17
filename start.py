#!/usr/bin/env python3
"""
Точка входа для Railway - избегает проблем с импортом app.py
"""
import os
import logging
from aiohttp import web

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("START: Direct Python execution starting...")
    
    # Импортируем create_app только при прямом запуске
    from app import create_app
    
    app = create_app()
    port = int(os.environ.get('PORT', 8080))
    host = os.environ.get('HOST', '0.0.0.0')
    
    logger.info(f"START: Server starting on {host}:{port}")
    logger.info("START: This should avoid gunicorn worker issues")
    
    # Запускаем сервер
    web.run_app(app, host=host, port=port)

if __name__ == '__main__':
    main()
