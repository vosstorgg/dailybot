#!/usr/bin/env python3
"""
Точка входа для Railway
"""
import logging
from app import application
from aiohttp import web
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    port = int(os.environ.get('PORT', 8080))
    host = os.environ.get('HOST', '0.0.0.0')
    
    logger.info(f"Starting DailyBot on {host}:{port}")
    web.run_app(application, host=host, port=port)

if __name__ == '__main__':
    main()
