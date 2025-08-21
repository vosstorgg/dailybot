# Настройка базы данных для DailyBot

## 🎯 Обзор

DailyBot теперь использует PostgreSQL базу данных для хранения:
- Данных пользователей и их регистрации
- Детальной аналитики активности
- Истории действий пользователей

## 🗄️ Схема базы данных

### Таблицы

1. **users** - Основная информация о пользователях
   - Telegram данные (ID, имя, username)
   - Астрологические данные (дата/время/место рождения)
   - Настройки (время прогнозов, язык)
   - Статус регистрации

2. **user_actions** - Журнал действий пользователей
   - Тип действия (команда, сообщение, запрос прогноза)
   - Время выполнения
   - Контекст действия

3. **user_analytics** - Ежедневная аналитика пользователей
   - Количество сообщений/команд
   - Время сессий
   - Оценка вовлеченности

## 🚀 Настройка на Railway

### 1. Создание базы данных PostgreSQL

1. Зайдите в ваш проект на Railway
2. Нажмите "Add Service" → "Database" → "PostgreSQL"
3. Railway автоматически создаст базу данных и сгенерирует URL подключения

### 2. Получение URL подключения

1. Перейдите в созданную базу данных
2. Во вкладке "Connect" найдите "Connection URL"
3. Скопируйте полный URL (format: `postgresql://username:password@host:port/database`)

### 3. Настройка переменных окружения

Добавьте следующие переменные в ваш Railway проект:

```bash
# Основная база данных (продакшн)
DATABASE_URL=postgresql://username:password@host:port/database

# Тестовая база данных (опционально)
DATABASE_URL_TEST=postgresql://username:password@host:port/database_test

# Окружение
ENVIRONMENT=production
```

### 4. Автоматическая инициализация

При первом запуске приложение автоматически:
- Создаст все необходимые таблицы
- Настроит индексы для производительности
- Подготовит структуру для аналитики

## 🔧 Локальная разработка

### 1. Использование Docker для PostgreSQL

```bash
# Запуск PostgreSQL в Docker
docker run --name dailybot-postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=dailybot \
  -p 5432:5432 \
  -d postgres:15

# URL для локальной разработки
DATABASE_URL=postgresql://postgres:password@localhost:5432/dailybot
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Настройка .env файла

```env
# Скопируйте env.example в .env и заполните:
DATABASE_URL=postgresql://postgres:password@localhost:5432/dailybot
DATABASE_URL_TEST=postgresql://postgres:password@localhost:5432/dailybot_test
ENVIRONMENT=development

# Остальные переменные из env.example
BOT_TOKEN=your_bot_token
WEBHOOK_URL=https://your-domain.com
WEATHER_API_KEY=your_weather_api_key
```

## 📊 API для аналитики

### Получение аналитики пользователя

```bash
GET /analytics/user?user_id=123456&days=30
```

**Ответ:**
```json
{
  "user_info": {
    "name": "Иван",
    "telegram_user_id": 123456,
    "registered_at": "2024-01-15T10:30:00",
    "registration_complete": true
  },
  "analytics_period": {
    "days": 30,
    "active_days": 15
  },
  "totals": {
    "messages": 45,
    "commands": 28,
    "astro_requests": 12,
    "moon_requests": 5,
    "avg_engagement_score": 8.5
  },
  "most_used_commands": [
    ["/astro", 12],
    ["/moon", 5],
    ["/profile", 3]
  ],
  "daily_records": [
    {
      "date": "2024-01-15",
      "messages": 3,
      "commands": 2,
      "astro_requests": 1,
      "engagement_score": 7.0
    }
  ]
}
```

## 🎯 Типы аналитики

### Отслеживаемые действия

1. **REGISTRATION_STARTED** - Начало регистрации
2. **REGISTRATION_COMPLETED** - Завершение регистрации
3. **ASTRO_REQUEST** - Запрос астропрогноза
4. **MOON_REQUEST** - Запрос лунной информации
5. **PROFILE_VIEW** - Просмотр профиля
6. **HELP_REQUEST** - Запрос справки
7. **MESSAGE_SENT** - Отправка сообщения
8. **LOCATION_SHARED** - Отправка геолокации
9. **COMMAND_USED** - Использование команды

### Метрики

- **Вовлеченность**: автоматический расчет на основе активности
- **Сессии**: время от первого до последнего действия в день
- **Популярные команды**: статистика использования функций
- **Активные дни**: дни с активностью пользователя

## 🔒 Безопасность

### Производственная среда

1. **Используйте сильные пароли** для базы данных
2. **Ограничьте доступ** к базе данных только с серверов приложения
3. **Регулярно делайте бэкапы** важных данных
4. **Мониторьте подключения** и необычную активность

### Рекомендации Railway

- Railway автоматически шифрует соединения с базой данных
- Используйте внутренние сети Railway для безопасности
- Регулярно обновляйте зависимости

## 🚨 Устранение неполадок

### Проблемы с подключением

```bash
# Проверка доступности базы данных
psql "postgresql://username:password@host:port/database" -c "SELECT version();"
```

### Логи подключения

Приложение выводит подробные логи инициализации базы данных:

```
INFO - Initializing database...
INFO - Database connection initialized
INFO - Database tables created
INFO - Database initialized successfully
```

### Распространенные ошибки

1. **"DATABASE_URL not found"** - проверьте переменные окружения
2. **"Connection refused"** - проверьте доступность базы данных
3. **"Table doesn't exist"** - приложение создаст таблицы автоматически при первом запуске

## 📈 Мониторинг

### Проверка состояния

```bash
# Health check с информацией о БД
GET /
```

### Логи приложения

Следите за логами для:
- Ошибок подключения к БД
- Медленных запросов
- Проблем с аналитикой

## 🔄 Миграция данных

Если у вас есть существующие данные пользователей, создайте скрипт миграции для переноса в новую схему базы данных.

## 🎉 Готово!

После настройки ваш DailyBot будет:
- ✅ Сохранять всех пользователей в PostgreSQL
- ✅ Отслеживать детальную аналитику
- ✅ Предоставлять API для анализа данных
- ✅ Автоматически создавать резервные копии (через Railway)

Для получения дополнительной помощи обращайтесь к документации Railway или PostgreSQL.
