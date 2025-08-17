"""
Сервис для работы с астрономическими данными через WeatherAPI
"""
import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from aiohttp import ClientSession

logger = logging.getLogger(__name__)

# Конфигурация
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
WEATHER_API_BASE = 'http://api.weatherapi.com/v1'

# Глобальный кэш для астро-данных
_astro_cache: Dict[str, Dict[str, Any]] = {}

class AstroDataCache:
    """Простой in-memory кэш для астрономических данных"""
    
    def __init__(self):
        self.cache = {}
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Получить данные из кэша"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            # Проверяем, не устарели ли данные (24 часа для астро-данных)
            if datetime.now() - timestamp < timedelta(hours=24):
                logger.info(f"Cache HIT for {key}")
                return data
            else:
                logger.info(f"Cache EXPIRED for {key}")
                del self.cache[key]
        return None
    
    def set(self, key: str, data: Dict[str, Any]):
        """Сохранить данные в кэш"""
        self.cache[key] = (data, datetime.now())
        logger.info(f"Cache SET for {key}")
    
    def clear(self):
        """Очистить кэш"""
        self.cache.clear()
        logger.info("Cache CLEARED")

# Глобальный экземпляр кэша
astro_cache = AstroDataCache()

async def get_moon_phase_data() -> Optional[Dict[str, Any]]:
    """
    Получить данные о фазе Луны (глобальные, не зависят от местоположения)
    Кэшируются на 24 часа
    """
    cache_key = f"moon_phase_{datetime.now().strftime('%Y-%m-%d')}"
    
    # Проверяем кэш
    cached_data = astro_cache.get(cache_key)
    if cached_data:
        return cached_data
    
    if not WEATHER_API_KEY:
        logger.error("WEATHER_API_KEY not configured")
        return None
    
    # Запрашиваем данные (используем Лондон как референсную точку для глобальных данных)
    url = f"{WEATHER_API_BASE}/astronomy.json"
    params = {
        'key': WEATHER_API_KEY,
        'q': 'London',  # Референсная точка
        'dt': datetime.now().strftime('%Y-%m-%d')
    }
    
    try:
        async with ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Извлекаем только нужные данные
                    astro_data = {
                        'moon_phase': data['astronomy']['astro']['moon_phase'],
                        'moon_illumination': int(data['astronomy']['astro']['moon_illumination']),
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'source': 'weatherapi.com'
                    }
                    
                    # Сохраняем в кэш
                    astro_cache.set(cache_key, astro_data)
                    
                    logger.info(f"Fetched moon phase data: {astro_data['moon_phase']} ({astro_data['moon_illumination']}%)")
                    return astro_data
                else:
                    logger.error(f"WeatherAPI error: {response.status}")
                    return None
                    
    except Exception as e:
        logger.error(f"Error fetching moon phase data: {e}")
        return None

async def get_daily_astro_summary() -> Dict[str, Any]:
    """
    Получить общую астрономическую сводку дня
    """
    logger.info("Generating daily astro summary...")
    
    # Получаем данные о Луне
    moon_data = await get_moon_phase_data()
    
    if not moon_data:
        return {
            'status': 'error',
            'message': 'Unable to fetch astronomical data'
        }
    
    # Формируем сводку
    summary = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'moon': {
            'phase': moon_data['moon_phase'],
            'illumination': moon_data['moon_illumination'],
            'description': _get_moon_description(moon_data)
        },
        'general_energy': _get_general_energy_description(moon_data),
        'recommendations': _get_daily_recommendations(moon_data),
        'cached': True if astro_cache.get(f"moon_phase_{datetime.now().strftime('%Y-%m-%d')}") else False
    }
    
    logger.info(f"Generated astro summary for {summary['date']}")
    return summary

def _get_moon_description(moon_data: Dict[str, Any]) -> str:
    """Генерирует описание лунной фазы"""
    phase = moon_data['moon_phase']
    illumination = moon_data['moon_illumination']
    
    descriptions = {
        'New Moon': f'🌑 Новолуние ({illumination}%) - время новых начинаний и планирования',
        'Waxing Crescent': f'🌒 Растущая Луна ({illumination}%) - период активного роста и развития',
        'First Quarter': f'🌓 Первая четверть ({illumination}%) - время принятия решений и действий',
        'Waxing Gibbous': f'🌔 Растущая Луна ({illumination}%) - период накопления энергии',
        'Full Moon': f'🌕 Полнолуние ({illumination}%) - пик энергии и эмоций',
        'Waning Gibbous': f'🌖 Убывающая Луна ({illumination}%) - время благодарности и отдачи',
        'Last Quarter': f'🌗 Последняя четверть ({illumination}%) - период очищения и освобождения',
        'Waning Crescent': f'🌘 Убывающая Луна ({illumination}%) - время отдыха и подготовки'
    }
    
    return descriptions.get(phase, f'🌙 {phase} ({illumination}%)')

def _get_general_energy_description(moon_data: Dict[str, Any]) -> str:
    """Генерирует описание общей энергетики дня"""
    phase = moon_data['moon_phase']
    illumination = moon_data['moon_illumination']
    
    if 'New Moon' in phase:
        return "Энергия обновления и свежих возможностей. Хорошее время для медитации и планирования."
    elif 'Waxing' in phase and illumination < 50:
        return "Растущая энергия способствует новым проектам и активным действиям."
    elif 'Full Moon' in phase or illumination > 90:
        return "Пиковая энергия! Время завершения дел и ярких эмоций. Будьте внимательны к чувствам."
    elif 'Waning' in phase:
        return "Убывающая энергия помогает отпустить лишнее и сосредоточиться на важном."
    else:
        return "Стабильная энергия. Хорошее время для повседневных дел и размышлений."

def _get_daily_recommendations(moon_data: Dict[str, Any]) -> list:
    """Генерирует рекомендации на день"""
    phase = moon_data['moon_phase']
    illumination = moon_data['moon_illumination']
    
    if 'New Moon' in phase:
        return [
            "🎯 Поставьте новые цели",
            "🧘 Практикуйте медитацию",
            "📝 Ведите дневник желаний"
        ]
    elif 'Waxing' in phase:
        return [
            "🚀 Начинайте новые проекты",
            "💪 Активно действуйте",
            "🌱 Развивайте навыки"
        ]
    elif 'Full Moon' in phase:
        return [
            "✨ Завершайте начатые дела",
            "❤️ Проявляйте благодарность",
            "🌊 Следите за эмоциями"
        ]
    else:  # Waning
        return [
            "🧹 Избавьтесь от лишнего",
            "🤝 Помогайте другим",
            "😴 Больше отдыхайте"
        ]

async def test_weather_api_connection() -> Dict[str, Any]:
    """Тестирует подключение к WeatherAPI"""
    if not WEATHER_API_KEY:
        return {
            'status': 'error',
            'message': 'WEATHER_API_KEY not configured'
        }
    
    try:
        # Простой запрос для проверки
        url = f"{WEATHER_API_BASE}/current.json"
        params = {
            'key': WEATHER_API_KEY,
            'q': 'London'
        }
        
        async with ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return {
                        'status': 'success',
                        'message': 'WeatherAPI connection successful'
                    }
                else:
                    return {
                        'status': 'error',
                        'message': f'WeatherAPI returned status {response.status}'
                    }
                    
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Connection error: {str(e)}'
        }

# Функция для очистки кэша (для тестирования)
def clear_cache():
    """Очищает кэш астрономических данных"""
    astro_cache.clear()
