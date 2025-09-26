#!/usr/bin/env python3
"""
Модуль для работы с FTP соединениями
Удаление старых файлов после загрузки новых
"""
import ftplib
import os
from typing import Dict, Any


class FTPManager:
    """Класс для управления FTP соединениями и удалением файлов"""
    
    @staticmethod
    def delete_file_via_ftp(storage_config, file_path):
        """Удаляем файл через FTP с подробными логами"""
        try:
            print(f"\n🗂️ ===== СТАРТ ОПЕРАЦИИ УДАЛЕНИЯ ФАЙЛА =====")
            print(f"🔌 FTPManager.delete_file_via_ftp() - начало операции")
            print(f"📁 Целевой файл: {file_path}")
            print(f"📋 Тип конфигурации хранилища: {type(storage_config)}")
            
            # Определяем формат storage_config (tuple из database.py или dict из database_api.py)
            if isinstance(storage_config, tuple):
                # Формат из database.py: [4]=connect_url, [5]=connect_port, [6]=username, [7]=password
                host = storage_config[4]  # connect_url
                port = storage_config[5]  # connect_port
                username = storage_config[6]  # username
                password = storage_config[7]  # password
                print(f"📊 Способ подключения: database.py tuple format")
            elif isinstance(storage_config, dict):
                # Формат из database_api.py (может быть с ключами как 'connect_url' или как 'url')
                host = storage_config.get("connect_url") or storage_config.get("url", "")
                port = storage_config.get("connect_port") or storage_config.get("port", "")
                username = storage_config.get("username") or storage_config.get("user", "")
                password = storage_config.get("password") or storage_config.get("pass", "")
                print(f"📊 Способ подключения: database_api.py dict format")
            else:
                raise ValueError(f"Неизвестный формат хранилища: {type(storage_config)}")
            
            print(f"🌐 ПОДКЛЮЧЕНИЕ К FTP:")
            print(f"   📡 Хост: {host}")
            print(f"   🔌 Порт: {port}")
            print(f"   👤 Пользователь: {username}")
            print(f"   🔒 Пароль: {'*' * len(password) if password else 'НЕТ'}")
            print(f"   🎯 Цель удаления: {file_path}")
            
            ftp = ftplib.FTP()
            ftp.connect(host, int(port))
            ftp.login(username, password)
            
            print(f"✅ ПОДКЛЮЧЕНИЕ К FTP УСПЕШНО")
            
            # Проверяем текущую директорию и существование файла
            try:
                current_dir = ftp.pwd()
                print(f"📂 Текущая директория FTP: {current_dir}")
            except:
                current_dir = "неизвестно"
                print(f"⚠️ Не удалось получить текущую директорию")
            
            # Проверяем существование файла
            try:
                file_size = ftp.size(file_path)
                if file_size is not None:
                    print(f"✅ ФАЙЛ НАЙДЕН НА FTP:")
                    print(f"   📁 Имя файла: {file_path}")
                    print(f"   📊 Размер: {file_size} байт")
                    print(f"   📂 Директория: {current_dir}")
                else:
                    print(f"⚠️ ФАЙЛ НЕ НАЙДЕН НА FTP:")
                    print(f"   📁 Поиск файла: {file_path}")
                    print(f"   📂 В директории: {current_dir}")
                    ftp.quit()
                    return False
            except Exception as e:
                print(f"⚠️ Проверка размера файла не удалась: {e}")
                print(f"🔄 ПРОДОЛЖАЕМ УДАЛЕНИЕ БЕЗ ПРОВЕРКИ...")
            
            print(f"🗑️ ПРОЦЕСС УДАЛЕНИЯ ФАЙЛА:")
            print(f"   📁 Удаляем: {file_path}")
            try:
                ftp.delete(file_path)
                print(f"✅ УДАЛЕНИЕ ЗАВЕРШЕНО УСПЕШНО")
                print(f"   🗂️ Файл удален: {file_path}")
            except Exception as e:
                print(f"❌ ОШИБКА УДАЛЕНИЯ ФАЙЛА:")
                print(f"   📁 Файл: {file_path}")
                print(f"   ⚠️ Ошибка: {e}")
                ftp.quit()
                return False
            
            ftp.quit()
            print(f"✅ ОТКЛЮЧЕНИЕ К FTP")
            print(f"🎉 ОПЕРАЦИЯ УДАЛЕНИЯ ЗАВЕРШЕНА УСПЕШНО!")
            print(f"🗂️ ===== КОНЕЦ ОПЕРАЦИИ УДАЛЕНИЯ ФАЙЛА =====\n")
            return True
            
        except Exception as e:
            print(f"\n❌ FАТАЛЬНАЯ ОШИБКА УДАЛЕНИЯ ЧЕРЕЗ FTP:")
            print(f"   📁 Файл: {file_path}")
            print(f"   ⚠️ Ошибка: {e}")
            print(f"🗂️ ===== ОШИБКА ОПЕРАЦИИ УДАЛЕНИЯ ФАЙЛА =====\n")
            return False
    
    @staticmethod
    def delete_local_file(file_path):
        """Удаляем локальный файл"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"✅ Локальный файл удален: {file_path}")
                return True
            else:
                print(f"⚠️ Локальный файл не найден: {file_path}")
                return False
        except Exception as e:
            print(f"❌ Ошибка удаления локального файла: {e}")
            return False
    
    @staticmethod
    def delete_file_from_storage(onserver, driver, storage_config=None):
        """Удаляем файл с хранилища (FTP или локально)"""
        try:
            print(f"🔧 FTPManager.delete_file_from_storage: onserver='{onserver}', driver={driver}")
            print(f"🔧 Параметры удаления: onserver='{onserver}', driver={driver}")
            print(f"🔧 Storage config type: {type(storage_config)}")
            
            if storage_config is not None:
                if isinstance(storage_config, tuple):
                    print(f"🔧 Storage tuple length: {len(storage_config)}")
                elif isinstance(storage_config, dict):
                    print(f"🔧 Storage dict keys: {storage_config.keys()}")
            else:
                print("🔧 НУЛЛ СТОРЕДЖ! ВОТ В ЧЕМ ПРОБЛЕМА!")
            
            if storage_config is None:
                print(f"⚠️ Нет конфигурации хранилища для driver={driver}")
                return False
            
            # Проверяем тип хранилища и выводим детальную диагностику
            if isinstance(storage_config, tuple) and len(storage_config) >= 8:
                storage_type = storage_config[2]  # type (1=FTP, 0=локальное)
                storage_host = storage_config[4]  # connect_url
                storage_port = storage_config[5]  # connect_port
                storage_user = storage_config[6]  # username
                print(f"📊 Найденное хранилище ID {driver}:")
                print(f"   🌐 Хост: {storage_host}")
                print(f"   🔌 Порт: {storage_port}")
                print(f"   👤 Пользователь: {storage_user}")
                print(f"   📦 Тип: {storage_type} (1=FTP, 0=локальное)")
            elif isinstance(storage_config, dict):
                storage_type = storage_config.get("type", 0)  # type
                storage_host = storage_config.get("connect_url", "")
                storage_port = storage_config.get("connect_port", "")
                storage_user = storage_config.get("username", "")
                print(f"📊 Найденное хранилище ID {driver} (dict формат):")
                print(f"   🌐 Хост: {storage_host}")
                print(f"   🔌 Порт: {storage_port}")
                print(f"   👤 Пользователь: {storage_user}")
                print(f"   📦 Тип: {storage_type} (1=FTP, 0=локальное)")
            else:
                storage_type = 0
                print(f"⚠️ Неизвестный формат конфигурации хранилища: {type(storage_config)}")
            
            # Формируем полный путь к файлу
            if isinstance(storage_config, tuple):
                storage_path = storage_config[8]  # path
            elif isinstance(storage_config, dict):
                storage_path = storage_config.get("path", "")
            else:
                storage_path = ""
            
            # Добавляем префикс /files если его нет
            if not onserver.startswith('/files'):
                onserver_with_prefix = f"/files/{onserver}"
            else:
                onserver_with_prefix = onserver
            
            full_path = f"{storage_path}{onserver_with_prefix}".replace('//', '/')
            
            print(f"🗂️ Полный путь к файлу: {full_path}")
            print(f"📂 Путь хранилища: {storage_path}")
            print(f"📁 Относительный путь: {onserver_with_prefix}")
            print(f"🔧 Тип хранилища: {storage_type} (1=FTP, 0=локальное)")
            
            if storage_type == 1:  # FTP хранилище
                print(f"🔌 Удаляем через FTP")
                return FTPManager.delete_file_via_ftp(storage_config, full_path)
            else:  # Локальное хранилище
                print(f"💾 Удаляем локально")
                return FTPManager.delete_local_file(full_path)
            
        except Exception as e:
            print(f"❌ Ошибка удаления файла с хранилища: {e}")
            return False
