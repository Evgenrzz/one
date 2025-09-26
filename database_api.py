#!/usr/bin/env python3
"""
Модуль для работы с API вместо прямого подключения к базе данных
"""
import requests
import re
import time

try:
    from .config import API_CONFIG, ENABLE_FUZZY_MATCHING, ENABLE_DETAILED_LOGGING
    from .lib.version_utils import VersionUtils
except ImportError:
    from config import API_CONFIG, ENABLE_FUZZY_MATCHING, ENABLE_DETAILED_LOGGING
    from lib.version_utils import VersionUtils


class DatabaseManagerAPI:
    def __init__(self, analyzer=None):
        self.analyzer = analyzer
        self._similar_apps_cache = {}  # Кэш для fuzzy matching
        
        # API конфигурация из config.py
        self.api_url = API_CONFIG['url']
        self.api_key = API_CONFIG['key']
        self.api_timeout = API_CONFIG['timeout']

    def api_request(self, action, params=None, data=None):
        """Выполняет запрос к API"""
        url = f"{self.api_url}?action={action}&key={self.api_key}"
        
        try:
            if data:
                response = requests.post(url, data=data, timeout=self.api_timeout)
            else:
                if params:
                    url += "&" + "&".join([f"{k}={v}" for k, v in params.items()])
                response = requests.get(url, timeout=self.api_timeout)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            return {"error": str(e)}

    def connect(self):
        """Имитация подключения для совместимости"""
        print("✅ API подключение готово")
        return True

    def disconnect(self):
        """Имитация отключения для совместимости"""
        print("🔒 API соединение закрыто")

    def check_version_in_apk_original(self, news_id, current_version):
        """Проверяем версию в поле apk-original и сравниваем с текущей версией"""
        try:
            response = self.api_request("check_apk_original", {
                "id": news_id,
                "version": current_version
            })
            
            if not response.get("success"):
                print(f"❌ Ошибка API: {response.get('error', 'Неизвестная ошибка')}")
                return True  # При ошибке считаем что нужно обновление
            
            data = response
            news_id = data["news_id"]
            attachment_name = data.get("attachment_name")
            apk_original_version = data.get("apk_original_version")
            need_update = data.get("need_update", True)
            
            if attachment_name:
                print(f"🔍 Найден attachment в apk-original: {attachment_name}")
            else:
                print(f"ℹ️ Поле apk-original не содержит attachment для новости {news_id}")
                return True  # Если нет attachment, считаем что нужно обновление
            
            if apk_original_version:
                print(f"📱 Версия в apk-original: {apk_original_version}")
                print(f"🌐 Версия на сайте: {current_version}")
                
                if need_update:
                    print(f"✅ Новая версия найдена: {apk_original_version} → {current_version}")
                    return True  # Нужно обновление
                else:
                    print(f"⏭️ Версия актуальна: {apk_original_version} >= {current_version}")
                    return False  # Не нужно обновление
            else:
                print(f"⚠️ Не удалось извлечь версию из attachment: {attachment_name}")
                return True  # Если не можем извлечь версию, считаем что нужно обновление
                
        except Exception as e:
            print(f"❌ Ошибка проверки версии в apk-original: {e}")
            return True  # При ошибке считаем что нужно обновление

    def check_if_update_needed(self, news_id, app_name, current_version, sha256_hash=None, package_name=None):
        """Проверяем нужно ли обновлять файл с улучшенной проверкой дублей"""
        try:
            # Проверяем дубли через API
            params = {
                "news_id": news_id,
                "app_name": app_name,
                "version": current_version
            }
            
            if sha256_hash:
                params["sha256_hash"] = sha256_hash
            if package_name:
                params["package_name"] = package_name
            
            response = self.api_request("check_duplicate", params)
            
            if not response.get("success"):
                print(f"❌ Ошибка проверки дублей: {response.get('error', 'Неизвестная ошибка')}")
                return True, None
            
            duplicates = response.get("duplicates", {})
            has_duplicates = response.get("has_duplicates", False)
            
            if not has_duplicates:
                print(f"📝 Новое приложение {app_name} версии {current_version} для новости {news_id}")
                return True, None
            
            # Проверяем точные дубли по SHA-256
            if "sha256" in duplicates:
                sha256_result = duplicates["sha256"]
                print(f"🔍 Найден точный дубль по SHA-256: {sha256_result['version']}")
                if self.analyzer:
                    self.analyzer.log_duplicate_found('sha256', sha256_result['version'], sha256_result['file_size'], 
                                                    'Точное совпадение содержимого файла')
                return False, sha256_result
            
            # Проверяем точные дубли по названию и версии
            if "exact" in duplicates:
                exact_result = duplicates["exact"]
                print(f"✅ Версия {current_version} уже актуальна")
                if self.analyzer:
                    self.analyzer.log_duplicate_found('name', app_name, current_version, 
                                                    'Точное совпадение названия и версии')
                return False, exact_result
            
            # Проверяем похожие файлы по размеру
            if "size" in duplicates:
                size_matches = duplicates["size"]
                print(f"🔍 Найдены файлы похожего размера ({len(size_matches)} шт.):")
                for match in size_matches:
                    size_diff = abs(match['file_size'] - (sha256_hash and len(sha256_hash) or 0))
                    print(f"   - {match['app_name']} v{match['version']} ({match['file_size']} байт)")
                
                # Возвращаем самый похожий по размеру
                return False, size_matches[0] if size_matches else None
            
            print(f"📝 Новое приложение {app_name} версии {current_version} для новости {news_id}")
            return True, None

        except Exception as e:
            print(f"❌ Ошибка проверки версии: {e}")
            return True, None

    def add_to_dle_files(self, news_id, app_name, version, file_extension, downloaded_filename, file_size, checksum, download_dir):
        """Добавляем запись в таблицу dle_files через API"""
        try:
            # Формируем читаемое имя файла для поля name
            readable_name = self._transliterate_cyrillic(app_name)
            readable_filename = f"{readable_name} {version}{file_extension}"
            
            print(f"📝 Формируем читаемое имя для dle_files.name: {readable_filename}")

            # Для onserver используем переданное имя файла (уже очищенное)
            relative_path = f"{download_dir.name}/{downloaded_filename}"
            
            print(f"🗂️ Путь в onserver (без timestamp): {relative_path}")
            print(f"📁 Загруженный файл: {downloaded_filename}")

            # Генерируем timestamp для поля date
            timestamp = str(int(time.time()))
            
            data = {
                "news_id": news_id,
                "name": readable_filename,
                "onserver": relative_path,
                "author": "sergeyAi",
                "date": timestamp,
                "dcount": 0,
                "size": file_size,
                "checksum": checksum,
                "driver": 2,
                "is_public": 0
            }
            
            response = self.api_request("add_dle_file", data=data)
            
            if response.get("success"):
                file_id = response["file_id"]
                print(f"✅ Файл добавлен в dle_files с ID: {file_id}")
                print(f"📁 name: {readable_filename}")
                print(f"🗂️ onserver: {relative_path}")
                return file_id
            else:
                print(f"❌ Ошибка добавления в dle_files: {response.get('error', 'Неизвестная ошибка')}")
                return None

        except Exception as e:
            print(f"❌ Ошибка добавления в dle_files: {e}")
            return None

    def update_dle_post(self, news_id, file_id, app_name, version, file_extension):
        """Обновляем поле apk-original в таблице dle_post через API"""
        try:
            data = {
                "news_id": news_id,
                "file_id": file_id,
                "app_name": app_name,
                "version": version,
                "file_extension": file_extension
            }
            
            response = self.api_request("update_apk_original", data=data)
            
            if response.get("success"):
                attachment = response["attachment"]
                print(f"✅ Обновлено поле apk-original для новости {news_id}: {attachment}")
                return True
            else:
                print(f"❌ Ошибка обновления dle_post: {response.get('error', 'Неизвестная ошибка')}")
                return False

        except Exception as e:
            print(f"❌ Ошибка обновления dle_post: {e}")
            return False

    def _transliterate_cyrillic(self, text):
        """Переводим кириллицу в латиницу"""
        cyrillic_to_latin = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
            'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
            'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
            'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch',
            'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
        }
        
        result = ""
        for char in text:
            if char in cyrillic_to_latin:
                result += cyrillic_to_latin[char]
            elif char == '+':
                result += ' '  # Заменяем + на пробелы
            else:
                result += char
        
        # Убираем множественные пробелы
        result = re.sub(r'\s+', ' ', result).strip()
        
        return result

    def add_to_tracking(self, news_id, app_name, version, file_size, file_path, checksum, source_url, sha256_hash=None, package_name=None, source_priority=0):
        """Добавляем запись в таблицу отслеживания через API"""
        try:
            data = {
                "news_id": news_id,
                "app_name": app_name,
                "version": version,
                "file_size": file_size,
                "file_path": str(file_path),
                "checksum": checksum,
                "source_url": source_url,
                "source_priority": source_priority
            }
            
            if sha256_hash:
                data["sha256_hash"] = sha256_hash
            if package_name:
                data["package_name"] = package_name
            
            response = self.api_request("add_tracking", data=data)
            
            if response.get("success"):
                tracking_id = response["tracking_id"]
                print(f"✅ Добавлена запись в таблицу отслеживания (ID: {tracking_id}):")
                print(f"   app_name: {app_name}")
                print(f"   version: {version}")
                print(f"   sha256: {sha256_hash[:16] if sha256_hash else 'N/A'}...")
                print(f"   package_name: {package_name or 'N/A'}")
                print(f"   source_priority: {source_priority}")
                return True
            else:
                print(f"❌ Ошибка добавления в tracking: {response.get('error', 'Неизвестная ошибка')}")
                return False

        except Exception as e:
            print(f"❌ Ошибка добавления в tracking: {e}")
            return False
    
    def find_similar_apps(self, app_name, threshold=0.8):
        """Находим похожие приложения с помощью fuzzy matching с кэшированием"""
        # Проверяем кэш
        cache_key = f"{app_name}_{threshold}"
        if cache_key in self._similar_apps_cache:
            return self._similar_apps_cache[cache_key]
        
        try:
            # Получаем все записи из tracking через API
            # Пока что возвращаем пустой список, так как API не поддерживает получение всех записей
            # В будущем можно добавить endpoint для получения всех уникальных app_name
            similar_apps = []
            
            # Кэшируем результат
            self._similar_apps_cache[cache_key] = similar_apps
            
            return similar_apps
            
        except Exception as e:
            print(f"❌ Ошибка поиска похожих приложений: {e}")
            return []
    
    def _calculate_similarity(self, name1, name2):
        """Вычисляем коэффициент схожести между названиями"""
        # Нормализуем названия
        name1_norm = re.sub(r'[^\w\s]', '', name1.lower()).strip()
        name2_norm = re.sub(r'[^\w\s]', '', name2.lower()).strip()
        
        # Простое сравнение по словам
        words1 = set(name1_norm.split())
        words2 = set(name2_norm.split())
        
        if not words1 or not words2:
            return 0
        
        # Вычисляем коэффициент схожести
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0
    
    def check_duplicate_by_content(self, sha256_hash):
        """Проверяем дубли по содержимому файла (SHA-256)"""
        try:
            response = self.api_request("check_duplicate", {
                "sha256_hash": sha256_hash
            })
            
            if response.get("success"):
                duplicates = response.get("duplicates", {})
                if "sha256" in duplicates:
                    result = duplicates["sha256"]
                    print(f"🔍 Найден точный дубль по содержимому: {result['app_name']} v{result['version']}")
                    return result
            
            return None
            
        except Exception as e:
            print(f"❌ Ошибка проверки дубля по содержимому: {e}")
            return None
    
    def check_duplicate_by_size(self, file_size, tolerance_percent=5):
        """Проверяем дубли по размеру файла с допустимым отклонением"""
        try:
            response = self.api_request("check_duplicate", {
                "file_size": file_size
            })
            
            if response.get("success"):
                duplicates = response.get("duplicates", {})
                if "size" in duplicates:
                    results = duplicates["size"]
                    print(f"🔍 Найдены файлы похожего размера ({len(results)} шт.):")
                    for result in results:
                        size_diff = abs(result['file_size'] - file_size)
                        size_diff_percent = (size_diff / file_size) * 100
                        print(f"   - {result['app_name']} v{result['version']} ({result['file_size']} байт, отклонение: {size_diff_percent:.1f}%)")
                    
                    # Возвращаем самый близкий по размеру
                    return results[0] if results else None
            
            return None
            
        except Exception as e:
            print(f"❌ Ошибка проверки дубля по размеру: {e}")
            return None
    
    def should_replace_existing(self, existing_data, new_source_priority):
        """Определяем, нужно ли заменить существующий файл новым с более высоким приоритетом"""
        if not existing_data:
            return False
        
        existing_priority = existing_data.get('source_priority', 0) if isinstance(existing_data, dict) else (existing_data[5] if len(existing_data) > 5 else 0)
        return new_source_priority > existing_priority
    
    def replace_lower_priority_file(self, existing_id, new_data):
        """Заменяем файл с более низким приоритетом"""
        try:
            # Обновляем существующую запись новыми данными через API
            data = {
                "file_id": existing_id,
                "name": new_data['app_name'],
                "onserver": new_data['file_path'],
                "date": int(time.time()),
                "size": new_data['file_size'],
                "checksum": new_data['checksum']
            }
            
            response = self.api_request("update_dle_file", data=data)
            
            if response.get("success"):
                print(f"🔄 Заменен файл с более низким приоритетом (ID: {existing_id})")
                return True
            else:
                print(f"❌ Ошибка замены файла: {response.get('error', 'Неизвестная ошибка')}")
                return False
            
        except Exception as e:
            print(f"❌ Ошибка замены файла: {e}")
            return False
    
    def delete_old_file_from_apk_original(self, news_id):
        """Удаляем старый файл из поля apk-original"""
        print("🔄 Вызывается обновленный метод delete_old_file_from_apk_original")
        # Для API версии пока что не реализуем удаление файлов
        # В будущем можно добавить соответствующий endpoint
        print("ℹ️ Удаление файлов через API пока не реализовано")
        return True
    
    
    def update_existing_file_in_dle_files(self, news_id, app_name, version, file_extension, downloaded_filename, file_size, checksum, download_dir):
        """Обновляем существующую запись в dle_files вместо создания новой"""
        print(f"🔄 Обновляем существующую запись в dle_files для новости {news_id}")
        try:
            # Получаем информацию о существующем файле через API
            response = self.api_request("get_post", {"id": news_id})
            
            if not response.get("success"):
                print(f"❌ Новость ID {news_id} не найдена")
                return None
            
            post_data = response["data"]
            xfields = post_data["xfields"]
            
            # Извлекаем старый attachment ID из поля apk-original
            old_attachment_match = re.search(r'apk-original\|\[attachment=(\d+):', xfields)
            
            if not old_attachment_match:
                print(f"ℹ️ Поле apk-original не содержит attachment для новости {news_id}")
                return None
            
            old_file_id = int(old_attachment_match.group(1))
            print(f"🔍 Найден существующий файл ID {old_file_id} в поле apk-original")
            
            # ПЕРЕХОД К ОБНОВЛЕНИЮ БД
            print(f"💾 ШАГ 6: Формируем данные для обновления базы данных")
            
            # Формируем новые данные для обновления
            readable_name = self._transliterate_cyrillic(app_name)
            new_readable_filename = f"{readable_name} {version}{file_extension}"
            new_onserver = f"{download_dir.name}/{downloaded_filename}"
            current_timestamp = int(time.time())
            
            print(f"📝 Новое имя файла: {new_readable_filename}")
            print(f"🗂️ Новый путь: {new_onserver}")
            
            # ШАГ 7: Обновляем запись в dle_files через API
            print(f"💾 ШАГ 7: Обновляем запись в базе данных dle_files")
            data = {
                "file_id": old_file_id,
                "name": new_readable_filename,
                "onserver": new_onserver,
                "date": current_timestamp,
                "size": file_size,
                "checksum": checksum
            }
            
            response = self.api_request("update_dle_file", data=data)
            
            if response.get("success"):
                print(f"✅ Обновлена запись ID {old_file_id} в dle_files")
                return old_file_id
            else:
                print(f"❌ Ошибка обновления файла в dle_files: {response.get('error', 'Неизвестная ошибка')}")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка обновления файла в dle_files: {e}")
            import traceback
            print(f"🔧 Traceback: {traceback.format_exc()}")
            return None

    def delete_old_file(self, old_file_id, news_id=None):
        """Безопасное удаление старого файла по ID из dle_files"""
        import os
        import logging
        from pathlib import Path
        from datetime import datetime
        try:
            from .config import FILE_DIRS, DELETION_LOG_FILE
        except ImportError:
            from config import FILE_DIRS, DELETION_LOG_FILE
        
        # Настраиваем логирование удаления файлов
        deletion_logger = logging.getLogger('file_deletion')
        deletion_logger.setLevel(logging.INFO)
        
        # Удаляем существующие обработчики
        for handler in deletion_logger.handlers[:]:
            deletion_logger.removeHandler(handler)
        
        # Создаем директорию для лог-файла, если не существует
        log_path = Path(DELETION_LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Добавляем файловый и консольный обработчики
        file_handler = logging.FileHandler(DELETION_LOG_FILE, encoding='utf-8')
        console_handler = logging.StreamHandler()
        
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        deletion_logger.addHandler(file_handler)
        deletion_logger.addHandler(console_handler)
        deletion_logger.propagate = False
        
        deletion_logger.info(f"🗑️ Начинаем удаление файла для old_file_id: {old_file_id}, news_id: {news_id}")
        
        try:
            # Получаем данные старого файла из БД
            response = self.api_request("get_file_info", data={"file_id": old_file_id})
            
            if not response.get("success"):
                deletion_logger.warning(f"❌ Запись с ID {old_file_id} не найдена в dle_files")
                return False
            
            file_data = response.get("file_info", {})
            onserver = file_data.get("onserver", "").strip()
            filename = file_data.get("name", "").strip()
            
            deletion_logger.info(f"📝 Данные старого файла - onserver: '{onserver}', name: '{filename}'")
            
            if not onserver:
                deletion_logger.warning(f"❌ Поле onserver пусто для файла ID {old_file_id}")
                return False
            
            # Очищаем путь от ведущих слешей и пробелов
            onserver = onserver.strip().lstrip('/')
            deletion_logger.info(f"🧹 Очищенный onserver путь: '{onserver}'")
            
            # Формируем кандидатов на удаление
            candidates = []
            for base_dir in FILE_DIRS:
                candidate_path = Path(base_dir) / onserver
                candidates.append((base_dir, candidate_path))
                deletion_logger.info(f"🎯 Кандидат на удаление: {candidate_path}")
            
            # Ищем и удаляем файл
            deleted = False
            for base_dir, candidate_path in candidates:
                deletion_logger.info(f"🔍 Проверяем путь: {candidate_path}")
                
                try:
                    # Проверяем, что путь находится внутри базовой директории (защита от path traversal)
                    base_path = Path(base_dir).resolve()
                    resolved_candidate = candidate_path.resolve()
                    
                    try:
                        # Проверяем, что resolved_candidate находится внутри base_path
                        resolved_candidate.relative_to(base_path)
                        deletion_logger.info(f"✅ Путь безопасен: {resolved_candidate}")
                    except ValueError:
                        deletion_logger.error(f"⚠️ Небезопасный путь (path traversal): {resolved_candidate}")
                        continue
                    
                    # Проверяем существование файла
                    if candidate_path.exists() and candidate_path.is_file():
                        file_size = candidate_path.stat().st_size
                        deletion_logger.info(f"📁 Файл найден: {candidate_path}, размер: {file_size} байт")
                        
                        # Удаляем файл
                        candidate_path.unlink()
                        deletion_logger.info(f"✅ Файл успешно удален: {candidate_path}")
                        deleted = True
                        break
                    else:
                        deletion_logger.info(f"❌ Файл не найден: {candidate_path}")
                        
                except Exception as e:
                    deletion_logger.error(f"❌ Ошибка при работе с файлом {candidate_path}: {e}")
                    import traceback
                    deletion_logger.error(f"🔧 Traceback: {traceback.format_exc()}")
                    continue
            
            if deleted:
                deletion_logger.info(f"✅ ИТОГ: Файл с ID {old_file_id} успешно удален")
                return True
            else:
                deletion_logger.warning(f"❌ ИТОГ: Файл с ID {old_file_id} не найден ни в одной из папок")
                return False
                
        except Exception as e:
            deletion_logger.error(f"❌ Критическая ошибка при удалении файла ID {old_file_id}: {e}")
            import traceback
            deletion_logger.error(f"🔧 Traceback: {traceback.format_exc()}")
            return False

