#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Простой нормализатор имен файлов для APK файлов
Переводит кириллицу в латиницу, заменяет символы на подчеркивания
"""

import re
import os


class FileNormalizer:
    """Нормализация имен файлов: кириллица → латиница, символы → подчеркивания"""

    @staticmethod
    def normalize_filename(filename):
        """Простая нормализация имени файла"""
        print(f"📝 Исходное имя файла: {filename}")
        
        # Разделяем имя файла и расширение
        name_part, extension = os.path.splitext(filename)
        
        # Переводим кириллицу в латиницу - только для name_part
        name_part = FileNormalizer.transliterate_cyrillic(name_part)
        
        # Простая замена символов в имени файла на подчеркивания
        name_part = name_part.replace(' ', '_')      # пробелы → _
        name_part = name_part.replace('.', '_')      # точки → _
        name_part = name_part.replace('+', '_')      # плюсы → _
        name_part = name_part.replace('-', '_')      # дефисы → _
        name_part = name_part.replace('(', '_')      # скобки → _
        name_part = name_part.replace(')', '_')
        name_part = name_part.replace('[', '_')
        name_part = name_part.replace(']', '_')
        name_part = name_part.replace('{', '_')
        name_part = name_part.replace('}', '_')
        
        # Удаляем все непонятные символы, оставляем только буквы, цифры и _
        name_part = re.sub(r'[^a-zA-Z0-9_]', '', name_part)
        
        # Убираем множественные подчеркивания
        name_part = re.sub(r'_+', '_', name_part)
        name_part = name_part.strip('_')
        
        # Все в нижний регистр для единообразия
        name_part = name_part.lower()
        extension = extension.lower()
        
        # ВТОРОЙ ЭТАП: убираем дублирующиеся суффиксы _xapk и _apk из имени файла
        if name_part.endswith('_xapk') and extension == '.xapk':
            name_part = name_part[:-5]  # убираем '_xapk' (5 символов)
            print(f"🔧 Удален дублирующийся суффикс _xapk из имени файла")
        elif name_part.endswith('_apk') and extension == '.apk':
            name_part = name_part[:-4]  # убираем '_apk' (4 символа)
            print(f"🔧 Удален дублирующийся суффикс _apk из имени файла")
        
        # Убираем повторные подчеркивания после удаления суффиксов
        name_part = re.sub(r'_+', '_', name_part).strip('_')
        
        # Собираем финальное имя файла
        normalized_filename = f"{name_part}{extension}"
        
        print(f"📝 Нормализованное имя: {normalized_filename}")
        return normalized_filename
    
    @staticmethod
    def transliterate_cyrillic(text):
        """Простой перевод кириллицы в латиницу"""
        # Основная таблица транслитерации кириллица → латиница
        cyrillic_to_latin = {
            'А': 'A', 'а': 'a', 'Б': 'B', 'б': 'b', 'В': 'V', 'в': 'v',
            'Г': 'G', 'г': 'g', 'Д': 'D', 'д': 'd', 'Е': 'E', 'е': 'e',
            'Ё': 'Yo', 'ё': 'yo', 'Ж': 'Zh', 'ж': 'zh', 'З': 'Z', 'з': 'z',
            'И': 'I', 'и': 'i', 'Й': 'Y', 'й': 'y', 'К': 'K', 'к': 'k',
            'Л': 'L', 'л': 'l', 'М': 'M', 'м': 'm', 'Н': 'N', 'н': 'n',
            'О': 'O', 'о': 'o', 'П': 'P', 'п': 'p', 'Р': 'R', 'р': 'r',
            'С': 'S', 'с': 's', 'Т': 'T', 'т': 't', 'У': 'U', 'у': 'u',
            'Ф': 'F', 'ф': 'f', 'Х': 'Kh', 'х': 'kh', 'Ц': 'Ts', 'ц': 'ts',
            'Ч': 'Ch', 'ч': 'ch', 'Ш': 'Sh', 'ш': 'sh', 'Щ': 'Sch', 'щ': 'sch',
            'Ъ': '', 'ъ': '', 'Ы': 'Y', 'ы': 'y', 'Ь': '', 'ь': '',
            'Э': 'E', 'э': 'e', 'Ю': 'Yu', 'ю': 'yu', 'Я': 'Ya', 'я': 'ya'
        }
        
        # Простая замена каждого символа
        result = ""
        for char in text:
            if char in cyrillic_to_latin:
                result += cyrillic_to_latin[char]
            else:
                result += char
        
        return result

    @staticmethod
    def clean_source_suffixes(filename):
        """Убираем суффиксы источников типа '_apkcombo.com'"""
        # Удаляем популярные суффиксы источников
        suffixes_to_remove = [
            '_apkcombo.com',
            'apkcombo',
            '.apkcombo',
            '_apkmirror.com',
            'apkmirror',
            '_pureapk',
            '_pureapk.com'
        ]
        
        clean_filename = filename
        for suffix in suffixes_to_remove:
            if suffix in clean_filename:
                clean_filename = clean_filename.replace(suffix, '')
        
        return clean_filename
    
    @staticmethod
    def remove_duplicate_extensions(filename):
        """Убираем дублирующиеся расширения из названия файла"""
        # Проверяем дублирующиеся расширения типа XAPK.xapk или APK.apk
        patterns = [
            r'_xapk\.xapk$',  # удаляем _xapk.xapk
            r'_apk\.apk$'     # удаляем _apk.apk
        ]
        
        for pattern in patterns:
            filename = re.sub(pattern, '', filename, flags=re.IGNORECASE)
        
        return filename


# Простой тест для проверки
if __name__ == "__main__":
    normalizer = FileNormalizer()
    
    test_files = [
        "Симулятор вождения UAZ Hunter 1.3.1_XAPK.xapk",
        "Russian+Car+Driver+Uaz+Hunter_1.2.9.xapk", 
        "MAPS.ME_ Offline maps GPS Nav_v16.1.71793-googleRelease.apk",
        "Adobe_Flash_Player_APK.apk"
    ]
    
    for test_file in test_files:
        print(f"\n=== Тестируем: {test_file} ===")
        result = normalizer.normalize_filename(test_file)
        print(f"РЕЗУЛЬТАТ: {result}")