#!/usr/bin/env python3
"""
Утилиты для работы с версиями приложений
Поддерживает семантическое версионирование и различные форматы
"""
import re
from typing import Optional, Tuple, List
from packaging import version as packaging_version


class VersionUtils:
    """Класс для работы с версиями приложений"""
    
    # Приоритеты источников (чем больше, тем выше приоритет)
    SOURCE_PRIORITIES = {
        'apkpure.com': 100,
        'apkcombo.com': 50,
        'unknown': 0
    }
    
    @staticmethod
    def extract_version_from_text(text: str) -> Optional[str]:
        """Извлекаем версию из любого текста с поддержкой различных форматов"""
        if not text:
            return None
            
        # Паттерны для поиска версий (от более специфичных к общим)
        version_patterns = [
            # Семантическое версионирование: 1.2.3, 1.2.3-beta, 1.2.3+build
            r'(\d+\.\d+\.\d+(?:-[a-zA-Z0-9\-\.]+)?(?:\+[a-zA-Z0-9\-\.]+)?)',
            # Версии с 4 цифрами: 1.2.3.4
            r'(\d+\.\d+\.\d+\.\d+)',
            # Версии с 2 цифрами: 1.2
            r'(\d+\.\d+)',
            # Одиночные цифры: 1
            r'(\d+)',
        ]
        
        for pattern in version_patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Берем самую длинную версию (обычно самая полная)
                best_version = max(matches, key=len)
                return best_version
        
        return None
    
    @staticmethod
    def normalize_version(version: str) -> str:
        """Нормализуем версию к стандартному формату"""
        if not version:
            return "1.0.0"
        
        # Убираем лишние символы
        version = re.sub(r'[^\d\.\-\+]', '', version)
        
        # Если версия слишком короткая, дополняем
        parts = version.split('.')
        if len(parts) == 1:
            version = f"{version}.0.0"
        elif len(parts) == 2:
            version = f"{version}.0"
        
        return version
    
    @staticmethod
    def compare_versions(version1: str, version2: str) -> int:
        """Сравниваем версии. Возвращает -1, 0, 1"""
        try:
            v1 = packaging_version.parse(VersionUtils.normalize_version(version1))
            v2 = packaging_version.parse(VersionUtils.normalize_version(version2))
            
            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1
            else:
                return 0
        except Exception:
            # Если не удалось распарсить, сравниваем как строки
            return -1 if version1 < version2 else (1 if version1 > version2 else 0)
    
    @staticmethod
    def is_version_newer(current: str, existing: str) -> bool:
        """Проверяем, является ли текущая версия новее существующей"""
        return VersionUtils.compare_versions(current, existing) > 0
    
    @staticmethod
    def extract_package_name_from_url(url: str) -> Optional[str]:
        """Извлекаем package name из URL"""
        if not url:
            return None
            
        # Паттерны для извлечения package name из различных URL
        patterns = [
            r'/([a-zA-Z0-9_\.]+)/?$',  # Последняя часть URL
            r'package=([a-zA-Z0-9_\.]+)',  # Параметр package
            r'id=([a-zA-Z0-9_\.]+)',  # Параметр id
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    @staticmethod
    def get_source_priority(source_url: str) -> int:
        """Получаем приоритет источника"""
        if not source_url:
            return VersionUtils.SOURCE_PRIORITIES['unknown']
        
        for source, priority in VersionUtils.SOURCE_PRIORITIES.items():
            if source in source_url.lower():
                return priority
        
        return VersionUtils.SOURCE_PRIORITIES['unknown']
    
    @staticmethod
    def extract_app_name_from_filename(filename: str) -> str:
        """Извлекаем название приложения из имени файла с улучшенной обработкой"""
        if not filename:
            return "Unknown"
        
        # Убираем расширение
        name = filename.replace('.xapk', '').replace('.apk', '').replace('.zip', '')
        
        # Убираем версию (различные форматы)
        version_patterns = [
            r'_\d+\.\d+\.\d+.*$',  # _1.2.3
            r'_\d+\.\d+.*$',       # _1.2
            r'v\d+\.\d+\.\d+.*$',  # v1.2.3
            r'v\d+\.\d+.*$',       # v1.2
            r'\d+\.\d+\.\d+.*$',   # 1.2.3
            r'\d+\.\d+.*$',        # 1.2
        ]
        
        for pattern in version_patterns:
            name = re.sub(pattern, '', name)
        
        # Обрабатываем специальные символы
        name = name.replace('+-+', ' ')
        name = name.replace('+', ' ')
        name = name.replace('-', ' ')
        name = name.replace('_', ' ')
        
        # Убираем множественные пробелы
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name if name else "Unknown"
    
    @staticmethod
    def fuzzy_match_app_names(name1: str, name2: str, threshold: float = 0.8) -> bool:
        """Проверяем схожесть названий приложений с помощью fuzzy matching"""
        if not name1 or not name2:
            return False
        
        # Нормализуем названия
        name1_norm = re.sub(r'[^\w\s]', '', name1.lower()).strip()
        name2_norm = re.sub(r'[^\w\s]', '', name2.lower()).strip()
        
        # Простое сравнение по словам
        words1 = set(name1_norm.split())
        words2 = set(name2_norm.split())
        
        if not words1 or not words2:
            return False
        
        # Вычисляем коэффициент схожести
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        similarity = intersection / union if union > 0 else 0
        
        return similarity >= threshold

