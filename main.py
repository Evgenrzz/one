#!/usr/bin/env python3
"""
Основной модуль системы обработки файлов из step4_links.txt
Скачивает файлы через парсеры APKCombo и APKPure и обновляет базу данных
Поддерживает множественные ссылки разделенные ;
"""
import asyncio
import os
import re
import logging
import traceback
from pathlib import Path
from datetime import datetime

try:
    from .config import LINKS_FILE, BASE_DOWNLOAD_DIR, ENABLE_SHA256_CHECK, ENABLE_FUZZY_MATCHING, ENABLE_SIZE_CHECK, ENABLE_DETAILED_LOGGING, FILE_DIRS, DELETION_LOG_FILE
    from .database_api import DatabaseManagerAPI as DatabaseManager
    from .version_extractor import VersionExtractor
    from .lib.file_downloader import FileDownloader
    from .lib.apkpure_downloader import APKPureDownloader
    from .lib.duplicate_analyzer import DuplicateAnalyzer
except ImportError:
    from config import LINKS_FILE, BASE_DOWNLOAD_DIR, ENABLE_SHA256_CHECK, ENABLE_FUZZY_MATCHING, ENABLE_SIZE_CHECK, ENABLE_DETAILED_LOGGING, FILE_DIRS, DELETION_LOG_FILE
    from database_api import DatabaseManagerAPI as DatabaseManager
    from version_extractor import VersionExtractor
    from lib.file_downloader import FileDownloader
    from lib.apkpure_downloader import APKPureDownloader
    from lib.duplicate_analyzer import DuplicateAnalyzer


class FileProcessor:
    def __init__(self):
        self.analyzer = DuplicateAnalyzer()
        self.db = DatabaseManager(analyzer=self.analyzer)
        self.version_extractor = VersionExtractor()
        
        # Создаем папку для текущего месяца
        self.download_dir = self.get_current_download_dir()
        self.downloader = FileDownloader(self.download_dir)
        
        # Настраиваем логирование
        self.setup_logging()
    
    def setup_logging(self):
        """Настраиваем логирование в файл logs/parser1_log.txt"""
        # Создаем папку logs если её нет
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Создаем имя файла лога
        log_filename = "parser1_log.txt"
        log_filepath = logs_dir / log_filename
        
        # Настраиваем логирование
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filepath, mode='w', encoding='utf-8'),  # mode='w' переписывает файл
                logging.StreamHandler()  # Также выводим в консоль
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"🚀 Запуск parser1 - лог файл: {log_filepath}")
    
    def get_current_download_dir(self):
        """Получаем папку для текущего месяца в формате год-месяц"""
        now = datetime.now()
        month_dir = f"{now.year}-{now.month:02d}"
        full_path = Path(BASE_DOWNLOAD_DIR) / month_dir
        full_path.mkdir(parents=True, exist_ok=True)
        return full_path

    def parse_link_line(self, line):
        """Парсим строку из файла step4_links.txt с поддержкой множественных ссылок"""
        # Формат: 1,[attachment=861:Apple Music_5.0.0.xapk],https://apkcombo.com/ru/apple-music/com.apple.android.music/
        # Новый формат: 22,[attachment=979:AIDA64_2.12.apk],https://apkcombo.com/ru/aida64/com.finalwire.aida64/;https://apkpure.com/ru/aida64/com.finalwire.aida64
        line = line.strip()
        if not line:
            return None

        parts = line.split(',', 2)
        if len(parts) != 3:
            return None

        news_id = parts[0].strip()
        attachment_info = parts[1].strip()
        urls_string = parts[2].strip()
        
        # Разделяем ссылки по ;
        urls = [url.strip() for url in urls_string.split(';') if url.strip()]
        
        if not urls:
            return None

        # Извлекаем информацию из attachment
        match = re.search(r'\[attachment=(\d+):([^\]]+)\]', attachment_info)
        if not match:
            return None

        old_file_id = match.group(1)
        filename = match.group(2)

        return {
            'news_id': int(news_id),
            'old_file_id': int(old_file_id),
            'filename': filename,
            'urls': urls
        }
    
    async def get_best_url_from_multiple(self, urls, app_name):
        """Получаем лучшую ссылку из множественных ссылок по версии"""
        if len(urls) == 1:
            return urls[0], None
        
        self.logger.info(f"🔍 Найдено {len(urls)} ссылок для {app_name}")
        
        best_url = None
        best_version = None
        url_versions = []
        
        for i, url in enumerate(urls, 1):
            try:
                self.logger.info(f"  📱 Ссылка {i}: {url}")
                
                # Получаем версию с сайта
                version = await self.version_extractor.extract_version_from_page(url)
                if version:
                    url_versions.append((url, version))
                    self.logger.info(f"    ✅ Версия: {version}")
                    
                    # Сравниваем версии
                    if best_version is None or self.compare_versions(version, best_version) > 0:
                        best_version = version
                        best_url = url
                        self.logger.info(f"    🏆 Новая лучшая версия: {version}")
                else:
                    self.logger.warning(f"    ❌ Не удалось получить версию с {url}")
                    
            except Exception as e:
                self.logger.error(f"    ❌ Ошибка при обработке {url}: {e}")
        
        if best_url:
            self.logger.info(f"🎯 Выбрана лучшая ссылка: {best_url} (версия: {best_version})")
            return best_url, best_version
        else:
            self.logger.warning("⚠️ Не удалось получить версии ни с одной ссылки, используем первую")
            return urls[0], None
    
    def compare_versions(self, version1, version2):
        """Сравнивает две версии и возвращает 1 если v1 > v2, -1 если v1 < v2, 0 если равны"""
        if not version1 or not version2:
            return 0
            
        try:
            # Разбиваем версии на части и конвертируем в числа
            v1_parts = [int(x) for x in version1.split('.')]
            v2_parts = [int(x) for x in version2.split('.')]
            
            # Дополняем более короткую версию нулями
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))
            
            # Сравниваем по частям
            for i in range(max_len):
                if v1_parts[i] > v2_parts[i]:
                    return 1
                elif v1_parts[i] < v2_parts[i]:
                    return -1
            
            return 0
        except:
            # Если не удалось распарсить, сравниваем как строки
            if version1 > version2:
                return 1
            elif version1 < version2:
                return -1
            else:
                return 0

    def delete_old_file(self, old_file_id, news_id=None):
        """
        Безопасное удаление старого файла по его ID из dle_files.
        
        Args:
            old_file_id: ID файла в таблице dle_files
            news_id: ID новости (для логирования)
            
        Returns:
            bool: True если файл был успешно удален или не найден, False при ошибке
        """
        # Настраиваем логирование для удаления файлов
        deletion_logger = logging.getLogger('file_deletion')
        deletion_logger.setLevel(logging.INFO)
        
        # Убираем существующие handlers чтобы избежать дублирования
        deletion_logger.handlers.clear()
        
        # Добавляем handler для файла логов
        try:
            # Создаем директорию для лог-файла если её нет
            log_dir = Path(DELETION_LOG_FILE).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(DELETION_LOG_FILE, encoding='utf-8')
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            deletion_logger.addHandler(file_handler)
        except Exception as e:
            self.logger.warning(f"⚠️ Не удалось настроить лог файл удаления: {e}")
        
        # Добавляем handler для консоли
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        deletion_logger.addHandler(console_handler)
        
        try:
            deletion_logger.info(f"🗑️ Начинаем удаление старого файла. old_file_id={old_file_id}, news_id={news_id}")
            
            # Получаем информацию о старом файле из БД
            cursor = self.db.connection.cursor()
            
            select_query = "SELECT onserver, name FROM dle_files WHERE id = %s LIMIT 1"
            cursor.execute(select_query, (old_file_id,))
            result = cursor.fetchone()
            
            if not result:
                deletion_logger.info(f"ℹ️ Файл с ID {old_file_id} не найден в dle_files - нечего удалять")
                cursor.close()
                return True
                
            onserver, filename = result
            deletion_logger.info(f"📄 Найден файл в БД: name='{filename}', onserver='{onserver}'")
            
            if not onserver or not onserver.strip():
                deletion_logger.info(f"ℹ️ Поле onserver пусто для файла ID {old_file_id} - нечего удалять")
                cursor.close()
                return True
            
            # Очищаем onserver от ведущих слэшей и пробелов
            onserver = onserver.strip().lstrip('/')
            deletion_logger.info(f"📁 Очищенный путь onserver: '{onserver}'")
            
            # Формируем пути для поиска файла
            candidates = []
            for base_dir in FILE_DIRS:
                candidate_path = Path(base_dir) / onserver
                candidates.append((base_dir, candidate_path))
                deletion_logger.info(f"🔍 Кандидат для удаления: {candidate_path}")
            
            # Ищем и удаляем файл
            file_deleted = False
            
            for base_dir, candidate_path in candidates:
                try:
                    # Проверяем безопасность пути - файл должен быть внутри базовой директории
                    base_path_resolved = Path(base_dir).resolve()
                    candidate_resolved = candidate_path.resolve()
                    
                    try:
                        # Для Python >= 3.9
                        if hasattr(candidate_resolved, 'is_relative_to'):
                            is_safe = candidate_resolved.is_relative_to(base_path_resolved)
                        else:
                            # Для Python < 3.9
                            try:
                                candidate_resolved.relative_to(base_path_resolved)
                                is_safe = True
                            except ValueError:
                                is_safe = False
                    except Exception:
                        is_safe = False
                        
                    if not is_safe:
                        deletion_logger.warning(f"⚠️ Небезопасный путь обнаружен: {candidate_path} не находится в {base_dir}")
                        continue
                    
                    deletion_logger.info(f"✅ Путь безопасен: {candidate_path}")
                    
                    # Проверяем существование файла
                    if candidate_path.exists():
                        # Получаем размер файла перед удалением
                        file_size = candidate_path.stat().st_size
                        deletion_logger.info(f"📊 Файл найден! Размер: {file_size} байт, полный путь: {candidate_path}")
                        
                        # Удаляем файл
                        candidate_path.unlink()
                        deletion_logger.info(f"✅ Файл успешно удален: {candidate_path}")
                        
                        file_deleted = True
                        break
                    else:
                        deletion_logger.info(f"❌ Файл не существует: {candidate_path}")
                        
                except Exception as e:
                    deletion_logger.error(f"❌ Ошибка при обработке пути {candidate_path}: {e}")
                    deletion_logger.error(f"Traceback: {traceback.format_exc()}")
                    continue
            
            cursor.close()
            
            if file_deleted:
                deletion_logger.info(f"🎉 Файл удален успешно. old_file_id={old_file_id}, filename='{filename}'")
                return True
            else:
                deletion_logger.info(f"ℹ️ Файл не найден ни в одной из директорий. old_file_id={old_file_id}, filename='{filename}'")
                return True  # Возвращаем True, так как файл все равно отсутствует
            
        except Exception as e:
            deletion_logger.error(f"❌ Критическая ошибка при удалении файла old_file_id={old_file_id}: {e}")
            deletion_logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    async def process_single_link(self, link_data):
        """Обрабатываем одну ссылку с поддержкой множественных ссылок"""
        self.logger.info(f"\n🔄 Обрабатываем: {link_data['filename']} (ID: {link_data['news_id']})")

        # Извлекаем информацию о приложении
        app_name = self.version_extractor.extract_app_name_from_filename(link_data['filename'])
        file_version = self.version_extractor.extract_version_from_filename(link_data['filename'])

        self.logger.info(f"📱 Приложение: {app_name}")
        self.logger.info(f"🔢 Версия из файла: {file_version}")

        # Выбираем лучшую ссылку из множественных
        best_url, best_version = await self.get_best_url_from_multiple(link_data['urls'], app_name)
        
        # Обновляем данные ссылки
        link_data['url'] = best_url
        if best_version:
            self.logger.info(f"🎯 Используем версию с лучшей ссылки: {best_version}")
            page_version = best_version
        else:
            # Пытаемся получить версию со страницы (только для APKCombo)
            page_version = None
            if 'apkcombo.com' in best_url:
                try:
                    page_version = await self.version_extractor.extract_version_from_page(best_url)
                except Exception as e:
                    self.logger.warning(f"⚠️ Ошибка получения версии со страницы APKCombo: {e}")
                    page_version = None
            else:
                self.logger.info("ℹ️ Версия со страницы будет получена парсером APKPure")

        # Определяем финальную версию (ТОЛЬКО номер версии)
        final_version = self.version_extractor.get_version(link_data['filename'], page_version)
        
        # Убеждаемся что это чистая версия
        clean_version_for_check = self.version_extractor.extract_clean_version(final_version)

        self.logger.info(f"🏷️ Финальная версия (только номер): {clean_version_for_check}")

        # Извлекаем дополнительную информацию
        package_name = self.version_extractor.extract_package_name_from_url(link_data['url'])
        source_priority = self.version_extractor.get_source_priority(link_data['url'])
        
        self.logger.info(f"📦 Package name: {package_name or 'N/A'}")
        self.logger.info(f"⭐ Приоритет источника: {source_priority}")

        # Сначала проверяем версию в поле apk-original
        self.logger.info("🔍 Проверяем версию в поле apk-original...")
        need_update_by_apk_original = self.db.check_version_in_apk_original(link_data['news_id'], clean_version_for_check)
        
        if not need_update_by_apk_original:
            self.logger.info("⏭️ Пропускаем, версия в apk-original актуальна")
            self.analyzer.log_file_processed(app_name, clean_version_for_check, 0, 
                                           link_data['url'], is_new=False)
            return True

        # Если версия в apk-original устарела, загружаем обновление без проверки дублей
        self.logger.info("🔄 Версия в apk-original устарела, загружаем обновление...")
        
        # Пропускаем проверку дублей и сразу переходим к загрузке
        self.logger.info("📥 Начинаем загрузку файла...")

        # Определяем тип парсера и скачиваем файл
        try:
            if 'apkcombo.com' in link_data['url']:
                self.logger.info("🔧 Используем парсер APKCombo")
                downloaded_file, download_version = await self.downloader.download_from_apkcombo(link_data['url'])
            elif 'apkpure.com' in link_data['url']:
                self.logger.info("🔧 Используем парсер APKPure")
                # Создаем APKPure downloader с той же папкой загрузки
                apkpure_downloader = APKPureDownloader(self.download_dir)
                downloaded_file, download_version = await apkpure_downloader.download_from_apkpure(link_data['url'])
            else:
                self.logger.error(f"❌ Неподдерживаемый сайт: {link_data['url']}")
                return False

            if not downloaded_file:
                self.logger.error("❌ Не удалось скачать файл")
                return False

            # Если при скачивании получили версию, используем её
            if download_version and download_version != "Unknown":
                # Извлекаем только номер версии из download_version
                clean_download_version = self.version_extractor.extract_clean_version(download_version)
                clean_version_for_check = clean_download_version
                self.logger.info(f"🎯 Обновляем версию из процесса скачивания: {clean_version_for_check}")

            # Получаем информацию о файле
            file_size = downloaded_file.stat().st_size
            
            # Вычисляем чексуммы
            if ENABLE_SHA256_CHECK:
                self.logger.info("🔐 Вычисляем чексуммы...")
                checksum, sha256_hash = self.downloader.calculate_checksums_parallel(downloaded_file)
            else:
                self.logger.info("🔐 Вычисляем MD5...")
                checksum = self.downloader.calculate_checksum(downloaded_file)
                sha256_hash = None

            self.logger.info(f"📊 Размер файла: {file_size} байт")
            self.logger.info(f"🔐 MD5: {checksum}")
            if sha256_hash:
                self.logger.info(f"🔐 SHA-256: {sha256_hash[:16]}...")
            self.logger.info(f"🏷️ Финальная версия для БД: {clean_version_for_check}")
            self.logger.info(f"📁 Загруженный файл: {downloaded_file.name}")
            
            # Пропускаем проверку дублей, так как версия в apk-original устарела
            self.logger.info("🔄 Пропускаем проверку дублей, обновляем существующую запись...")

            # Получаем расширение файла
            file_extension = os.path.splitext(downloaded_file.name)[1]
            
            # Очищаем имя файла от суффиксов источников
            try:
                from .lib.file_normalizer import FileNormalizer
            except ImportError:
                from lib.file_normalizer import FileNormalizer
            clean_filename = FileNormalizer.clean_source_suffixes(downloaded_file.name)
            
            # Переименовываем файл на диске
            if clean_filename != downloaded_file.name:
                new_file_path = self.download_dir / clean_filename
                downloaded_file.rename(new_file_path)
                downloaded_file = new_file_path
                self.logger.info(f"📁 Файл переименован: {downloaded_file.name}")
            
            self.logger.info(f"🏷️ Чистая версия для БД: {clean_version_for_check}")
            
            # УДАЛЕНИЕ СТАРОГО ФАЙЛА - вызываем после успешной загрузки и вычисления хеша/размера
            self.logger.info("🗑️ Удаляем старый файл перед обновлением БД...")
            deletion_success = self.delete_old_file(link_data['old_file_id'], link_data['news_id'])
            if not deletion_success:
                self.logger.warning("⚠️ Не удалось удалить старый файл, но продолжаем обработку...")
            
            # Обновляем существующую запись в dle_files вместо создания новой
            self.logger.info("🔄 Обновляем существующую запись в dle_files...")
            file_id = self.db.update_existing_file_in_dle_files(
                link_data['news_id'],
                app_name,
                clean_version_for_check,
                file_extension,
                clean_filename,  # Передаем очищенное имя файла
                file_size,
                checksum,
                self.download_dir
            )

            if not file_id:
                self.logger.error("❌ Не удалось обновить запись в dle_files")
                return False

            # Обновляем dle_post с читаемым именем (используем тот же file_id)
            success = self.db.update_dle_post(
                link_data['news_id'],
                file_id,
                app_name,
                clean_version_for_check,
                file_extension
            )

            if not success:
                self.logger.error("❌ Не удалось обновить dle_post")
                return False

            # Добавляем в таблицу отслеживания с улучшенными полями
            self.db.add_to_tracking(
                link_data['news_id'],
                app_name,
                clean_version_for_check,  # ТОЛЬКО версия, например "1.8.3"
                file_size,
                downloaded_file,
                checksum,
                link_data['url'],
                sha256_hash=sha256_hash,
                package_name=package_name,
                source_priority=source_priority
            )

            self.logger.info(f"✅ Файл {clean_filename} успешно обработан с версией {clean_version_for_check}!")
            self.analyzer.log_file_processed(app_name, clean_version_for_check, file_size, 
                                           link_data['url'], is_new=True)
            return True

        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки файла: {e}")
            self.analyzer.log_processing_error(str(e), f"для {app_name}")
            return False

    async def process_links_file(self):
        """Обрабатываем файл со ссылками"""
        if not os.path.exists(LINKS_FILE):
            self.logger.error(f"❌ Файл {LINKS_FILE} не найден")
            return

        self.logger.info(f"📄 Читаем файл: {LINKS_FILE}")

        with open(LINKS_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        self.logger.info(f"📊 Найдено {len(lines)} строк")

        # Начинаем анализ дублей
        self.analyzer.start_processing()

        processed = 0
        errors = 0

        for i, line in enumerate(lines, 1):
            self.logger.info(f"\n{'='*50}")
            self.logger.info(f"📝 Строка {i}/{len(lines)}")

            link_data = self.parse_link_line(line)
            if not link_data:
                self.logger.warning(f"⚠️ Не удалось распарсить строку: {line.strip()}")
                continue

            # Проверяем что это поддерживаемая ссылка (проверяем все URLs в списке)
            has_supported_url = False
            for url in link_data['urls']:
                if 'apkcombo.com' in url or 'apkpure.com' in url:
                    has_supported_url = True
                    break
            
            if not has_supported_url:
                self.logger.info(f"⏭️ Пропускаем неподдерживаемые ссылки: {link_data['urls']}")
                continue

            try:
                success = await self.process_single_link(link_data)
                if success:
                    processed += 1
                else:
                    errors += 1

            except Exception as e:
                self.logger.error(f"❌ Критическая ошибка обработки строки {i}: {e}")
                errors += 1
                continue

        # Завершаем анализ дублей
        self.analyzer.end_processing()

        self.logger.info(f"\n{'='*50}")
        self.logger.info(f"📊 ИТОГИ:")
        self.logger.info(f"✅ Успешно обработано: {processed}")
        self.logger.info(f"❌ Ошибок: {errors}")
        self.logger.info(f"📄 Всего строк: {len(lines)}")


