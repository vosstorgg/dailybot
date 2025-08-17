"""
WSGI entry point for gunicorn
"""
import os
import logging
from app import create_app

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("WSGI: Initializing application...")

# Создаем приложение для gunicorn
application = create_app()

logger.info(f"WSGI: Application type: {type(application)}")
logger.info("WSGI: Application ready!")

# Проверим, что это действительно aiohttp Application
from aiohttp.web_app import Application
if isinstance(application, Application):
    logger.info("WSGI: ✅ Correct aiohttp Application instance")
else:
    logger.error(f"WSGI: ❌ Wrong type: {type(application)}")
