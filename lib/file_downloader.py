#!/usr/bin/env python3
"""
Модуль для скачивания файлов с APKCombo.com
Интегрирован в систему обработки файлов
"""
import asyncio
import os
import re
import hashlib
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
import cloudscraper
import requests
from urllib.parse import urlparse, unquote
from ..config import BROWSER_ARGS, USER_AGENT, BASE_DOWNLOAD_DIR, CLOUDFLARE_TIMEOUT, PAGE_LOAD_TIMEOUT, DOWNLOAD_TIMEOUT
from .file_normalizer import FileNormalizer


class FileDownloader:
    def __init__(self, download_dir):
        self.download_dir = download_dir
        
        # Добавляем нормализатор файлов
        try:
            from .file_normalizer import FileNormalizer
            self.normalizer = FileNormalizer()
        except:
            self.normalizer = None

    def extract_filename_from_response(self, response, original_url="", default_name="downloaded_file.apk"):
        """Извлекает правильное имя файла из HTTP ответа"""
        filename = default_name
        
        # Пробуем получить из Content-Disposition заголовка
        content_disposition = response.headers.get('Content-Disposition', '')
        if 'filename=' in content_disposition:
            # Ищем filename="..." либо filename*=UTF-8''name
            patterns = [
                r'filename\*?=["\']?([^"\';\s]+)["\']?',
                r'filename\*?=([^;]+)'
            ]
            for pattern in patterns:
                matches = re.findall(pattern, content_disposition, re.IGNORECASE)
                if matches:
                    filename = matches[0].strip()
                    break
        
        # Пробуем извлечь из URL
        if default_name == filename:
            try:
                parsed = urlparse(original_url or response.url)
                url_filename = parsed.path.split('/')[-1]
                decoded_filename = unquote(url_filename)
                
                if decoded_filename and ('.apk' in decoded_filename or '.xapk' in decoded_filename):
                    filename = decoded_filename
            except:
                pass
        
        # Проверяем что у файла есть расширение
        if not any(ext in filename.lower() for ext in ['.apk', '.xapk']):
            if 'content-type' in str(response.headers).lower():
                if 'xapk' in str(response.headers):
                    filename = filename.rstrip('.') + '.xapk'
                else:
                    filename = filename.rstrip('.') + '.apk'
        
        # Очищаем имя файла от недопустимых символов
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = filename.strip()
        
        return filename if filename else default_name

    def download_with_cloudscraper(self, url, directory):
        """Скачивает файл используя cloudscraper с правильным именем"""
        try:
            scraper = cloudscraper.create_scraper()
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            scraper.headers.update(headers)
            
            print(f"📥 Скачиваем через cloudscraper: {url}")
            response = scraper.get(url, stream=True, allow_redirects=True, timeout=60)
            
            if response.status_code == 200:
                # Извлекаем правильное имя файла
                filename = self.extract_filename_from_response(response, url)
                
                filepath = directory / filename
                print(f"📁 Имя файла: {filename}")
                
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                if filepath.exists() and self.is_valid_apk(filepath):
                    size_mb = filepath.stat().st_size / 1024 / 1024
                    print(f"✅ Файл скачан cloudscraper: {filepath.name} ({size_mb:.2f} MB)")
                    return filepath
            
            return None
        except Exception as e:
            print(f"❌ Ошибка cloudscraper: {e}")
            return None

    def is_valid_apk(self, file_path):
        """Проверяет корректность APK файла"""
        if not file_path.exists():
            return False
        
        file_size = file_path.stat().st_size
        if file_size < 1024:
            return False
            
        with open(file_path, 'rb') as f:
            header = f.read(4)
            return header.startswith(b'PK')

    def calculate_checksum(self, file_path):
        """Вычисляем MD5 чексумму файла"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def calculate_sha256(self, file_path):
        """Вычисляем SHA-256 чексумму файла для более надежной проверки дублей"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):  # Увеличили размер буфера
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def calculate_checksums_parallel(self, file_path):
        """Вычисляем MD5 и SHA-256 параллельно для ускорения"""
        import threading
        
        md5_result = [None]
        sha256_result = [None]
        
        def calc_md5():
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hash_md5.update(chunk)
            md5_result[0] = hash_md5.hexdigest()
        
        def calc_sha256():
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hash_sha256.update(chunk)
            sha256_result[0] = hash_sha256.hexdigest()
        
        # Запускаем оба вычисления параллельно
        t1 = threading.Thread(target=calc_md5)
        t2 = threading.Thread(target=calc_sha256)
        
        t1.start()
        t2.start()
        
        t1.join()
        t2.join()
        
        return md5_result[0], sha256_result[0]

    def normalize_filename(self, filename):
        """Нормализуем имя файла согласно требованиям"""
        return FileNormalizer.normalize_filename(filename)

    def format_filename_for_attachment(self, filename):
        """Форматируем имя файла для поля apk-original"""
        return FileNormalizer.format_filename_for_attachment(filename)

    def extract_version_from_filename(self, filename):
        """Извлекаем версию из имени файла"""
        # Ищем паттерн версии в имени файла
        version_patterns = [
            r'_(\d+\.\d+\.\d+)',  # _5.0.0
            r'_(\d+\.\d+)',       # _5.0
            r'v(\d+\.\d+\.\d+)',  # v5.0.0
            r'(\d+\.\d+\.\d+)',   # 5.0.0
        ]

        for pattern in version_patterns:
            match = re.search(pattern, filename)
            if match:
                return match.group(1)

        return "1.0.0"  # Версия по умолчанию

    def extract_app_name_from_filename(self, filename):
        """Извлекаем название приложения из имени файла"""
        # Убираем расширение и версию
        name = filename.replace('.xapk', '').replace('.apk', '')
        # Убираем версию если есть
        name = re.sub(r'_\d+\.\d+.*$', '', name)
        return name

    async def wait_for_cloudflare(self, page, max_wait=120):
        """Ждем прохождения проверки Cloudflare"""
        print("🔄 Проверяем наличие Cloudflare...")
        for i in range(max_wait):
            await asyncio.sleep(1)
            try:
                current_url = page.url
                page_title = await page.title()
                # Проверяем индикаторы Cloudflare
                cf_indicators = [
                    "div.cf-browser-verification",
                    "div.cf-checking-browser",
                    "[data-ray]",
                    "h1:has-text('Checking your browser')",
                    "h1:has-text('Just a moment')"
                ]
                is_cf_active = False
                for indicator in cf_indicators:
                    try:
                        element = await page.query_selector(indicator)
                        if element:
                            is_cf_active = True
                            break
                    except:
                        continue
                # Проверяем по заголовку и URL
                if ("just a moment" in page_title.lower() or
                    "checking" in page_title.lower() or
                    "cloudflare" in current_url.lower()):
                    is_cf_active = True
                if not is_cf_active:
                    print("✅ Cloudflare проверка пройдена или отсутствует")
                    return True
                if i % 10 == 0:
                    print(f"⏳ Ждем Cloudflare... ({i+1}/{max_wait})")
            except Exception as e:
                print(f"   Ошибка при проверке Cloudflare: {e}")
                continue
        print("⚠️ Превышено время ожидания Cloudflare")
        return False

    async def download_file_from_r2_url(self, page, r2_url, expected_filename=None):
        """Скачиваем файл по r2 ссылке - сначала пробуем cloudscraper, потом Playwright"""
        print(f"🔗 Переходим по r2 ссылке для скачивания...")
        
        # Метод 1: Пробуем cloudscraper для прямого скачивания  
        print("🔧 Пробуем cloudscraper для обхода Cloudflare...")
        downloaded_file = self.download_with_cloudscraper(r2_url, self.download_dir)
        
        if downloaded_file and self.is_valid_apk(downloaded_file):
            # Если есть ожидаемое имя файла и файл был получен с другим именем - переименовываем
            if expected_filename and downloaded_file.name != expected_filename:
                try:
                    new_filepath = self.download_dir / expected_filename
                    if not new_filepath.exists():
                        downloaded_file.rename(new_filepath)
                        print(f"🏷️ Переименован в: {expected_filename}")
                        downloaded_file = new_filepath
                except Exception as e:
                    print(f"⚠️ Не удалось переименовать: {e}")
            
            # Нормализуем имя файла после успешного скачивания через cloudscraper
            original_filename = downloaded_file.name
            
            if self.normalizer and hasattr(self.normalizer, 'normalize_filename'):
                normalized_name = self.normalizer.normalize_filename(original_filename)
                if normalized_name != original_filename:
                    normalized_filepath = self.download_dir / normalized_name
                    if not normalized_filepath.exists():
                        downloaded_file.rename(normalized_filepath)
                        downloaded_file = normalized_filepath
                        print(f"🔄 Файл нормализован: {original_filename} → {normalized_name}")
            
            print(f"✅ Файл успешно скачан через cloudscraper!")
            return downloaded_file
        elif downloaded_file:
            print("⚠️ Cloudscraper скачал файл, но он не корректен")
            # Удаляем некорректный файл если есть
            try:
                downloaded_file.unlink()
            except:
                pass
        
        # Метод 2: Fallback через Playwright
        print("🔄 Переключаемся на Playwright как резервный метод...")
        
        download_started = False
        download_obj = None

        async def handle_download(download):
            nonlocal download_started, download_obj
            download_obj = download
            download_started = True
            print("🎯 Загрузка началась через Playwright!")

        page.on("download", handle_download)

        try:
            print("🌐 Переходим по ссылке через Playwright...")
            await page.goto(r2_url, wait_until="domcontentloaded", timeout=60000)
            
            # Ждем Cloudflare
            await self.wait_for_cloudflare(page, max_wait=120)
            
            # Ждем начала загрузки
            for i in range(30):
                if download_started:
                    break
                await asyncio.sleep(1)
                if i % 5 == 0:
                    print(f"⏳ Ожидание начала загрузки Playwright... ({i+1}/30)")
            
            if download_started:
                # Определяем имя файла для Playwright
                suggested_filename = download_obj.suggested_filename if download_obj else None
                if expected_filename and expected_filename.endswith(('.apk', '.xapk')):
                    suggested_filename = expected_filename
                    print(f"📁 Используем ожидаемое имя файла: {expected_filename}")
                elif not suggested_filename:
                    # Пытаемся извлечь из URL
                    if "filename" in r2_url:
                        match = re.search(r'filename%253D%2522([^%]+)', r2_url)
                        if match:
                            suggested_filename = match.group(1).replace('%2520', ' ')
                    
                    if not suggested_filename:
                        suggested_filename = "downloaded_file.apk"

                print(f"📁 Имя файла Playwright: {suggested_filename}")
                
                # Нормализуем имя если есть нормализатор
                if self.normalizer and hasattr(self.normalizer, 'normalize_filename'):
                    normalized_filename = self.normalizer.normalize_filename(suggested_filename)
                else:
                    # Базовое нормализование имени файла
                    normalized_filename = re.sub(r'[<>:"/\\|?*]', '', suggested_filename).strip()
                    if not normalized_filename.endswith(('.apk', '.xapk')):
                        normalized_filename += '.apk'

                final_file = self.download_dir / normalized_filename
                await download_obj.save_as(str(final_file))
                
                if final_file.exists() and self.is_valid_apk(final_file):
                    # Нормализуем имя файла после успешного скачивания
                    original_filename = final_file.name
                    
                    if self.normalizer and hasattr(self.normalizer, 'normalize_filename'):
                        normalized_name = self.normalizer.normalize_filename(original_filename)
                        if normalized_name != original_filename:
                            normalized_filepath = self.download_dir / normalized_name
                            if not normalized_filepath.exists():
                                final_file.rename(normalized_filepath)
                                final_file = normalized_filepath
                                print(f"🔄 Файл нормализован: {original_filename} → {normalized_name}")
                    
                    size_mb = final_file.stat().st_size / 1024 / 1024
                    print(f"✅ Файл успешно скачан через Playwright: {final_file.name}")
                    print(f"📊 Размер файла: {size_mb:.2f} MB")
                    return final_file
                else:
                    print("⚠️ Скачанный файл не прошёл валидацию APK")
                    try:
                        final_file.unlink()
                    except:
                        pass
            else:
                print("❌ Загрузка через Playwright не началась.")
        except Exception as e:
            print(f"❌ Ошибка Playwright: {e}")

        return None

    async def extract_version_from_page(self, app_url):
        """Извлекаем версию со страницы приложения"""
        try:
            print(f"🔍 Получаем версию со страницы: {app_url}")
            
            # Создаем браузер для получения версии
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=BROWSER_ARGS
                )
                context = await browser.new_context(
                    user_agent=USER_AGENT
                )
                page = await context.new_page()
                
                try:
                    await page.goto(app_url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
                    await self.wait_for_cloudflare(page, max_wait=60)
                    await asyncio.sleep(3)

                    # Ищем версию в div.version
                    version_selectors = [
                        'div.version',
                        '.version',
                        '[class*="version"]',
                        '.app-version'
                    ]
                    
                    for selector in version_selectors:
                        try:
                            element = await page.query_selector(selector)
                            if element:
                                version_text = await element.inner_text()
                                # Извлекаем только номер версии
                                version_match = re.search(r'(\d+\.\d+\.\d+)', version_text)
                                if version_match:
                                    version = version_match.group(1)
                                    print(f"✅ Найдена версия на странице: {version}")
                                    return version
                        except:
                            continue
                    
                    print("⚠️ Версия не найдена на странице")
                    return None
                    
                finally:
                    await context.close()
                    await browser.close()
                    
        except Exception as e:
            print(f"❌ Ошибка получения версии со страницы: {e}")
            return None

    async def download_from_apkcombo(self, app_url):
        """Скачиваем файл с apkcombo.com"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage"
                ]
            )
            context = await browser.new_context(
                accept_downloads=True,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            try:
                print(f"📱 Открываем страницу приложения: {app_url}")
                await page.goto(app_url, wait_until="domcontentloaded", timeout=60000)
                # Ждем прохождения Cloudflare если есть
                await self.wait_for_cloudflare(page, max_wait=60)
                await asyncio.sleep(3)

                # Получаем версию со страницы
                page_version = await self.extract_version_from_page(app_url)

                # Шаг 1: Ищем ссылку "Скачать APK"
                print("🔍 Ищем ссылку 'Скачать APK'...")
                download_link = None
                selectors_to_try = [
                    "a.button.is-success.is-fullwidth",
                    "a.button.is-success",
                    "a[href*='/download/apk']",
                    "a[href*='/download/']",
                    "div.download a.button"
                ]
                for selector in selectors_to_try:
                    try:
                        print(f"   Пробуем селектор: {selector}")
                        elements = await page.query_selector_all(selector)
                        for element in elements:
                            href = await element.get_attribute("href")
                            text = await element.inner_text()
                            print(f"     Найден элемент: href={href}, text={text.strip()[:30]}")
                            if href and ('/download/' in href or 'apk' in href.lower()):
                                download_link = element
                                print(f"   ✅ Выбран элемент с href: {href}")
                                break
                        if download_link:
                            break
                    except Exception as e:
                        print(f"     Ошибка с селектором {selector}: {e}")
                        continue
                if not download_link:
                    raise Exception("Не удалось найти ссылку 'Скачать APK'")

                href = await download_link.get_attribute("href")
                if not href:
                    raise Exception("Не удалось получить href ссылки")
                # Приводим ссылку к полному виду
                if href.startswith('/'):
                    download_page_url = f"https://apkcombo.com{href}"
                else:
                    download_page_url = href
                print(f"➡️ Ссылка на страницу загрузки: {download_page_url}")

                # Шаг 2: Переходим на страницу загрузки
                await page.goto(download_page_url, wait_until="domcontentloaded", timeout=120000)
                await self.wait_for_cloudflare(page, max_wait=60)
                await asyncio.sleep(5)

                # Шаг 3: Ищем первый вариант файла в ul.file-list
                print("🔍 Ищем первый вариант файла в ul.file-list...")
                variant_selectors = [
                    "ul.file-list li a",
                    "ul.file-list a",
                    ".file-list li a",
                    ".file-list a"
                ]
                variant = None
                for selector in variant_selectors:
                    try:
                        print(f"   Ищем варианты с селектором: {selector}")
                        variant = await page.wait_for_selector(selector, timeout=15000)
                        if variant:
                            print(f"   ✅ Найден вариант с селектором: {selector}")
                            break
                    except:
                        continue
                if not variant:
                    raise Exception("Не удалось найти варианты загрузки в ul.file-list")

                # Получаем информацию о файле
                try:
                    file_type_element = await variant.query_selector("span.vtype span, .type-apk, .type-xapk")
                    file_type = await file_type_element.inner_text() if file_type_element else "APK"
                    version_element = await variant.query_selector("span.vername")
                    version = await version_element.inner_text() if version_element else "Unknown"
                    print(f"📦 Найден файл: {version} ({file_type})")
                except:
                    file_type = "APK"
                    version = "Unknown"
                
                # Формируем ожидаемое имя файла из данных сайта
                expected_filename = None
                if version != "Unknown" and file_type:
                    # Создаем правильное имя файла из версии и типа
                    import re
                    clean_version = re.sub(r'[<>:"/\\|?*]', '', version.strip())
                    clean_type = file_type.strip().upper()
                    
                    if 'XAPK' in clean_type:
                        expected_filename = f"{clean_version}_{file_type}.xapk"
                    else:
                        expected_filename = f"{clean_version}_{file_type}.apk"
                    
                    print(f"📝 Формируем ожидаемое имя файла: {expected_filename}")

                # Получаем r2 ссылку
                r2_href = await variant.get_attribute("href")
                if not r2_href:
                    raise Exception("Не удалось найти r2 ссылку варианта загрузки")

                # Приводим r2 ссылку к полному виду
                if r2_href.startswith('/'):
                    r2_url = f"https://apkcombo.com{r2_href}"
                else:
                    r2_url = r2_href
                print(f"🔗 Найдена r2 ссылка: {r2_url}")

                # Шаг 4: Скачиваем файл по r2 ссылке
                downloaded_file = await self.download_file_from_r2_url(page, r2_url, expected_filename)
                
                # Возвращаем версию со страницы если есть, иначе версию из файла
                final_version = page_version if page_version else version
                return downloaded_file, final_version
                
            except Exception as e:
                print(f"❌ Ошибка: {e}")
                print(f"🔍 Текущий URL: {page.url}")
                # Сохраняем скриншот для отладки
                try:
                    await page.screenshot(path="debug_screenshot.png", full_page=True)
                    print("📸 Скриншот сохранен: debug_screenshot.png")
                except:
                    pass
                return None, None
            finally:
                await context.close()
                await browser.close()
                print("🔒 Браузер закрыт")
