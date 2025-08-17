#!/usr/bin/env python3
"""
Скрипт для создания миграций базы данных
"""
import os
import subprocess
import sys

def create_initial_migration():
    """Создает начальную миграцию с таблицами"""
    try:
        # Убеждаемся что есть DATABASE_URL для миграций (может быть тестовая)
        if not os.getenv('DATABASE_URL'):
            print("⚠️  DATABASE_URL не установлена")
            print("Установите тестовую DATABASE_URL для создания миграций:")
            print("export DATABASE_URL='postgresql://user:password@localhost/test_db'")
            return False
        
        print("🚀 Создание начальной миграции...")
        
        # Создаем миграцию
        result = subprocess.run([
            sys.executable, '-m', 'alembic', 'revision', '--autogenerate',
            '-m', 'Initial tables: users, forecasts, astronomical_cache, activities'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Миграция создана успешно!")
            print(result.stdout)
            return True
        else:
            print("❌ Ошибка создания миграции:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def apply_migration():
    """Применяет миграции к базе данных"""
    try:
        print("🔄 Применение миграций...")
        
        result = subprocess.run([
            sys.executable, '-m', 'alembic', 'upgrade', 'head'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Миграции применены успешно!")
            print(result.stdout)
            return True
        else:
            print("❌ Ошибка применения миграций:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

if __name__ == '__main__':
    print("🗄️  Управление миграциями DailyBot")
    print("=" * 40)
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'create':
            create_initial_migration()
        elif command == 'apply':
            apply_migration()
        elif command == 'both':
            if create_initial_migration():
                apply_migration()
        else:
            print("Доступные команды:")
            print("  create - создать миграцию")
            print("  apply  - применить миграции")
            print("  both   - создать и применить")
    else:
        print("Использование: python create_migration.py [create|apply|both]")
        print("\nДля Railway:")
        print("1. Создайте PostgreSQL базу в Railway")
        print("2. Скопируйте DATABASE_URL в переменные окружения")
        print("3. Запустите: python create_migration.py both")
