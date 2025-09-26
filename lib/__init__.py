#!/usr/bin/env python3
"""
Библиотека модулей для системы обработки файлов
"""

# Импортируем только базовые модули без зависимостей
from .file_normalizer import FileNormalizer
from .file_deleter import FileDeleter

# Условные импорты для модулей с внешними зависимостями
try:
    from .file_downloader import FileDownloader
    from .apkpure_downloader import APKPureDownloader
    __all__ = ['FileNormalizer', 'FileDeleter', 'FileDownloader', 'APKPureDownloader']
except ImportError:
    # Если зависимости не установлены, доступны только FileNormalizer и FileDeleter
    __all__ = ['FileNormalizer', 'FileDeleter']
