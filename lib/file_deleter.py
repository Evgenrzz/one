#!/usr/bin/env python3
"""
Модуль для удаления файлов по новой простой логике
"""

import os
try:
    # Импорт для прямого использования в корень
    from config import STORAGE_PATHS
except ImportError:
    # Импорт для использования как модуль
    try:
        from ..config import STORAGE_PATHS
    except ImportError:
        # Fallback если другие методы не работают
        STORAGE_PATHS = {
            1: {'base_path': "/home2/n1/files", 'name': "Driver #1 (Store #1)"},
            2: {'base_path': "/www/n2.anplus1.com/files", 'name': "Driver #2 (Store #2)"}
        }


class FileDeleter:
    """Класс для удаления файлов на основе driver и onserver"""
    
    @staticmethod
    def delete_old_file_simple(filename, onserver, driver):
        """Простое удаление файла на основе driver и onserver"""
        print(f"🔧 УДАЛЕНИЕ СТАРОГО ФАЙЛА ПО НОВОЙ ЛОГИКЕ:")
        print(f"   📝 Имя файла БД: {filename}")
        print(f"   📁 Путь в БД (onserver): {onserver}")
        print(f"   🎯 Драйвер: {driver}")
        
        try:
            # Получаем конфигурацию из хранилищ
            storage_config = STORAGE_PATHS.get(driver)
            if not storage_config:
                print(f"❌ Неизвестный driver {driver}")
                return False
            
            base_path = storage_config['base_path']
            storage_name = storage_config['name']
            
            # Формируем полный путь к файлу
            full_file_path = os.path.join(base_path, onserver)
            full_file_path = full_file_path.replace('\\', '/')  # Для кроссплатформы
            
            print(f"📂 Корневая папка ({storage_name}): {base_path}")
            print(f"🔗 Файл ищем по пути: {full_file_path}")
            
            # Расширенные логи проверок пути
            print(f"🔍 ПРОВЕРКА ПУТИ К ФАЙЛУ:")
            print(f"   📁 Базовый путь из конфига: {base_path}")
            print(f"   📎 Относительный путь (onserver): {onserver}")
            print(f"   🛤️ Полный абсолютный путь: {full_file_path}")
            
            # Проверяем, существует ли файл
            if os.path.exists(full_file_path):
                file_stat = os.stat(full_file_path)
                file_size = file_stat.st_size
                print(f"   📊 Размер файла: {file_size} байт")
                print(f"   🌍 Статус доступа: ок")
                
                try:
                    # Удаляем файл
                    os.remove(full_file_path)
                    print(f"✅ Старый файл удален успешно из: {full_file_path}")
                    print(f"🔧 УДАЛЕНИЕ ЗАВЕРШЕНО: {filename} из {storage_name}")
                    return True
                except OSError as e:
                    print(f"❌ Ошибка удаления файла {e}: не удалось удалить {full_file_path}")
                    return False
            else:
                print(f"⚠️ ФАЙЛ НЕ НАЙДЕН В СИСТЕМЕ: {full_file_path}")
                print(f"🔍 Диагностика отсутствия файла:")
                print(f"   📂 Проверяем доступность базовой папки {base_path}: {os.path.exists(base_path)}")
                if os.path.exists(base_path):
                    parent_dir = os.path.dirname(full_file_path)
                    print(f"   📂 Существует ли родительская папка {parent_dir}: {os.path.exists(parent_dir)}")
                    if os.path.exists(parent_dir):
                        print(f"   📋 Список файлов в папке {parent_dir}:")
                        try:
                            files_in_dir = os.listdir(parent_dir)
                            for file_item in files_in_dir:
                                print(f"      - {file_item}")
                        except OSError as list_e:
                            print(f"      ❌ Ошибка чтения папки: {list_e}")
                
                # Попробуем альтернативные пути если не найден
                return FileDeleter._try_alternative_paths(filename, onserver, driver, storage_name, base_path)
                
        except Exception as e:
            print(f"❌ Критическая ошибка удаления файла: {e}")
            return False
    
    @staticmethod
    def _try_alternative_paths(filename, onserver, driver, storage_name, base_path):
        """Попробовать найти файл по альтернативным путям"""
        print(f"🔍 ПОИСК ПО АЛЬТЕРНАТИВНЫМ ПУТЯМ:")
        
        # 1. Попробуем найти файл без префикса пути onserver 
        alt_paths_to_try = [
            os.path.join(base_path, os.path.basename(onserver)),
            os.path.join(base_path, "files", onserver),
            os.path.join(base_path, "files", os.path.basename(onserver))
        ]
        
        print(f"📂 Альтернативные пути для поиска файла {filename}:")
        
        for i, alt_path in enumerate(alt_paths_to_try):
            alt_full_path = alt_path.replace('\\', '/')
            print(f"   {i+1}. {alt_full_path}")
            
            if os.path.exists(alt_full_path):
                try:
                    file_stat = os.stat(alt_full_path)
                    file_size = file_stat.st_size
                    print(f"   ✅ Файл найден!: {alt_full_path} (размер: {file_size} байт)")
                    
                    os.remove(alt_full_path)
                    print(f"   🔧 Файл удален успешно: {alt_full_path}")
                    return True
                except OSError as delete_e:
                    print(f"   ❌ Ошибка удаления {alt_full_path}: {delete_e}")
            else:
                print(f"   ⚠️ Не найден: {alt_full_path}")
        
        print(f"❌ Файл {filename} не найден ни по одному пути")
        return False
    
    @staticmethod
    def get_storage_path(driver):
        """Получает путь хранилища по driver"""
        storage_config = STORAGE_PATHS.get(driver)
        if storage_config:
            return storage_config['base_path'], storage_config['name']
        else:
            return None, f"Driver #{driver} (Unknown)"
    
    @staticmethod
    def build_full_path(base_path, onserver):
        """Формирует полный путь к файлу"""
        full_file_path = os.path.join(base_path, onserver)
        full_file_path = full_file_path.replace('\\', '/')  # Для кроссплатформы
        return full_file_path


# Быстрая функция для прямого использования
def delete_file_by_path(filename, onserver, driver):
    """Простая функция для удаления файла по пути"""
    return FileDeleter.delete_old_file_simple(filename, onserver, driver)
