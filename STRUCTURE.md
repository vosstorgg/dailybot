# 📁 Структура проекта DailyBot

## 🎯 Основные файлы

### 🐍 Python код
- **`app.py`** - Основное приложение aiohttp с webhook логикой
- **`start.py`** - Точка входа для Railway (упрощенный запуск)

### ⚙️ Конфигурация развертывания
- **`Procfile`** - Команда запуска для Railway (`web: python start.py`)
- **`railway.json`** - Настройки Railway (рестарт политика, команда)
- **`nixpacks.toml`** - Конфигурация сборки Nixpacks
- **`runtime.txt`** - Версия Python (3.12)

### 📦 Зависимости
- **`requirements.txt`** - Python пакеты (aiohttp, aiohttp-cors, aiohttp[speedups])
- **`env.example`** - Шаблон переменных окружения

### 📚 Документация
- **`README.md`** - Основная документация проекта
- **`STRUCTURE.md`** - Этот файл (структура проекта)

## 🔄 Поток запуска

```
Railway → Procfile → start.py → app.py → aiohttp server
```

1. **Railway** читает `Procfile`
2. **Procfile** запускает `python start.py`
3. **start.py** импортирует приложение из `app.py`
4. **app.py** создает aiohttp приложение
5. **Сервер** запускается на порту 8080

## 🌐 Переменные окружения

Настраиваются в Railway UI:
- `BOT_TOKEN` - токен Telegram бота от @BotFather
- `WEBHOOK_URL` - URL приложения Railway (автоматически)
- `PORT` - порт сервера (автоматически 8080)
- `HOST` - хост сервера (автоматически 0.0.0.0)

## 📡 API структура

```
/ (GET)              → health_check()     → Статус и информация
/webhook (POST)      → webhook()          → Обработка сообщений Telegram  
/set_webhook (GET)   → set_webhook()      → Настройка webhook (браузер)
/set_webhook (POST)  → set_webhook()      → Настройка webhook (API)
```

## 🎯 Ключевые принципы

- ✅ **Простота** - минимум файлов, максимум функциональности
- ✅ **Асинхронность** - все операции неблокирующие
- ✅ **Надежность** - обработка ошибок и логирование
- ✅ **Масштабируемость** - готовность к расширению функций
- ✅ **Railway-first** - оптимизация под платформу развертывания
