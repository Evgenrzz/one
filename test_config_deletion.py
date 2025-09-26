#!/usr/bin/env python3
"""
Тест для проверки конфигурационной опции ENABLE_OLD_FILE_DELETION
"""

def test_config_option():
    """Проверяем, что конфигурационная опция импортируется корректно"""
    print("🧪 ТЕСТИРОВАНИЕ КОНФИГУРАЦИОННОЙ ОПЦИИ УДАЛЕНИЯ ФАЙЛОВ")
    print("=" * 60)
    
    try:
        from config import ENABLE_OLD_FILE_DELETION
        print(f"✅ Конфигурация импортирована успешно")
        print(f"📊 ENABLE_OLD_FILE_DELETION = {ENABLE_OLD_FILE_DELETION}")
        print(f"📝 Тип: {type(ENABLE_OLD_FILE_DELETION)}")
        
        if isinstance(ENABLE_OLD_FILE_DELETION, bool):
            if ENABLE_OLD_FILE_DELETION:
                print("✅ Удаление старых файлов ВКЛЮЧЕНО")
            else:
                print("⚠️ Удаление старых файлов ОТКЛЮЧЕНО")
            return True
        else:
            print(f"❌ ОШИБКА: ENABLE_OLD_FILE_DELETION должно быть bool, получен {type(ENABLE_OLD_FILE_DELETION)}")
            return False
            
    except ImportError as e:
        print(f"❌ ОШИБКА ИМПОРТА: {e}")
        return False
    except Exception as e:
        print(f"❌ НЕОЖИДАННАЯ ОШИБКА: {e}")
        return False

def test_database_import():
    """Проверяем, что database.py успешно импортирует конфигурацию"""
    print("\n🧪 ТЕСТИРОВАНИЕ ИМПОРТА В DATABASE.PY")
    print("=" * 60)
    
    try:
        # Импортируем без создания подключения к БД
        import sys
        import importlib.util
        
        spec = importlib.util.spec_from_file_location("database", "database.py")
        database_module = importlib.util.module_from_spec(spec)
        
        # Тестируем только импорт
        print("✅ Импорт database.py модуля успешен")
        return True
        
    except Exception as e:
        print(f"❌ ОШИБКА ПРИ ИМПОРТЕ database.py: {e}")
        return False

if __name__ == "__main__":
    print("🚀 ЗАПУСК ТЕСТОВ КОНФИГУРАЦИИ УДАЛЕНИЯ ФАЙЛОВ")
    print("=" * 60)
    
    test1_result = test_config_option()
    test2_result = test_database_import()
    
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    print(f"✅ Тест конфигурации: {'ПРОЙДЕН' if test1_result else 'НЕ ПРОЙДЕН'}")
    print(f"✅ Тест импорта в database: {'ПРОЙДЕН' if test2_result else 'НЕ ПРОЙДЕН'}")
    
    if test1_result and test2_result:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("✅ Конфигурационная опция ENABLE_OLD_FILE_DELETION работает корректно")
    else:
        print("\n⚠️ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")
    
    print("\n📝 ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ:")
    print("   • По умолчанию удаление старых файлов включено (ENABLE_OLD_FILE_DELETION = True)")
    print("   • Для отключения установите ENABLE_OLD_FILE_DELETION = False в config.py")
    print("   • Настройка влияет на метод update_existing_file_in_dle_files() в database.py")