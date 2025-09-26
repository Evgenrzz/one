#!/usr/bin/env python3
"""
Модуль для анализа дублей и метрик
"""
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path


class DuplicateAnalyzer:
    """Класс для анализа дублей и сбора метрик"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.metrics = {
            'total_processed': 0,
            'duplicates_found': 0,
            'duplicates_by_sha256': 0,
            'duplicates_by_name': 0,
            'duplicates_by_size': 0,
            'similar_apps_found': 0,
            'files_replaced_by_priority': 0,
            'processing_errors': 0,
            'start_time': None,
            'end_time': None
        }
        self.duplicate_log = []
    
    def start_processing(self):
        """Начинаем обработку"""
        self.metrics['start_time'] = datetime.now()
        self.log(f"🚀 Начало обработки файлов")
    
    def end_processing(self):
        """Завершаем обработку"""
        try:
            self.metrics['end_time'] = datetime.now()
            duration = (self.metrics['end_time'] - self.metrics['start_time']).total_seconds()
            self.log(f"🏁 Обработка завершена за {duration:.2f} секунд")
            self._save_metrics()
            self._print_summary()
        except Exception as e:
            self.log(f"❌ Ошибка при завершении обработки: {e}")
            # Пробуем хотя бы вывести сводку
            try:
                self._print_summary()
            except:
                pass
    
    def log_duplicate_found(self, duplicate_type: str, app_name: str, version: str, 
                           reason: str, similarity: float = None):
        """Логируем найденный дубль"""
        self.metrics['duplicates_found'] += 1
        
        # Проверяем, существует ли счетчик для данного типа
        counter_key = f'duplicates_by_{duplicate_type}'
        if counter_key in self.metrics:
            self.metrics[counter_key] += 1
        
        duplicate_info = {
            'timestamp': datetime.now().isoformat(),
            'type': duplicate_type,
            'app_name': app_name,
            'version': version,
            'reason': reason,
            'similarity': similarity
        }
        
        self.duplicate_log.append(duplicate_info)
        self.log(f"🔍 Дубль ({duplicate_type}): {app_name} v{version} - {reason}")
    
    def log_similar_apps(self, app_name: str, similar_apps: List[Dict]):
        """Логируем найденные похожие приложения"""
        self.metrics['similar_apps_found'] += len(similar_apps)
        self.log(f"🔍 Найдено {len(similar_apps)} похожих приложений для {app_name}")
        
        for similar in similar_apps[:3]:  # Логируем только топ-3
            self.log(f"   - {similar['app_name']} (схожесть: {similar['similarity']:.2f})")
    
    def log_file_replaced(self, old_app: str, new_app: str, reason: str):
        """Логируем замену файла"""
        self.metrics['files_replaced_by_priority'] += 1
        self.log(f"🔄 Заменен файл: {old_app} -> {new_app} ({reason})")
    
    def log_processing_error(self, error: str, context: str = ""):
        """Логируем ошибку обработки"""
        self.metrics['processing_errors'] += 1
        self.log(f"❌ Ошибка: {error} {context}")
    
    def log_file_processed(self, app_name: str, version: str, file_size: int, 
                          source: str, is_new: bool = True):
        """Логируем обработанный файл"""
        self.metrics['total_processed'] += 1
        status = "новый" if is_new else "дубль"
        self.log(f"📁 Обработан {status} файл: {app_name} v{version} ({file_size} байт) из {source}")
    
    def log(self, message: str):
        """Общий метод логирования"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        
        # Записываем в файл
        log_file = self.log_dir / f"processing_{datetime.now().strftime('%Y%m%d')}.log"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_message + '\n')
    
    def _save_metrics(self):
        """Сохраняем метрики в JSON файл"""
        try:
            metrics_file = self.log_dir / f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # Создаем копию метрик для сериализации
            serializable_metrics = self.metrics.copy()
            
            # Конвертируем datetime объекты в строки
            if serializable_metrics['start_time']:
                serializable_metrics['start_time'] = serializable_metrics['start_time'].isoformat()
            if serializable_metrics['end_time']:
                serializable_metrics['end_time'] = serializable_metrics['end_time'].isoformat()
            
            # Добавляем информацию о дублях
            serializable_metrics['duplicate_details'] = self.duplicate_log
            
            with open(metrics_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_metrics, f, ensure_ascii=False, indent=2)
            
            self.log(f"📊 Метрики сохранены в {metrics_file}")
        except Exception as e:
            self.log(f"❌ Ошибка сохранения метрик: {e}")
            # Пробуем сохранить без дублей
            try:
                simple_metrics = {
                    'total_processed': self.metrics['total_processed'],
                    'duplicates_found': self.metrics['duplicates_found'],
                    'duplicates_by_sha256': self.metrics['duplicates_by_sha256'],
                    'duplicates_by_name': self.metrics['duplicates_by_name'],
                    'duplicates_by_size': self.metrics['duplicates_by_size'],
                    'similar_apps_found': self.metrics['similar_apps_found'],
                    'files_replaced_by_priority': self.metrics['files_replaced_by_priority'],
                    'processing_errors': self.metrics['processing_errors'],
                    'start_time': self.metrics['start_time'].isoformat() if self.metrics['start_time'] else None,
                    'end_time': self.metrics['end_time'].isoformat() if self.metrics['end_time'] else None
                }
                
                simple_metrics_file = self.log_dir / f"metrics_simple_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(simple_metrics_file, 'w', encoding='utf-8') as f:
                    json.dump(simple_metrics, f, ensure_ascii=False, indent=2)
                
                self.log(f"📊 Упрощенные метрики сохранены в {simple_metrics_file}")
            except Exception as e2:
                self.log(f"❌ Критическая ошибка сохранения метрик: {e2}")
    
    def _print_summary(self):
        """Выводим сводку по обработке"""
        print("\n" + "="*60)
        print("📊 СВОДКА ПО ОБРАБОТКЕ ДУБЛЕЙ")
        print("="*60)
        
        total = self.metrics['total_processed']
        duplicates = self.metrics['duplicates_found']
        errors = self.metrics['processing_errors']
        
        print(f"📁 Всего обработано файлов: {total}")
        print(f"🔍 Найдено дублей: {duplicates}")
        print(f"❌ Ошибок: {errors}")
        
        if total > 0:
            duplicate_rate = (duplicates / total) * 100
            print(f"📈 Процент дублей: {duplicate_rate:.1f}%")
        
        print("\n🔍 РАСПРЕДЕЛЕНИЕ ДУБЛЕЙ ПО ТИПАМ:")
        print(f"   SHA-256 (содержимое): {self.metrics['duplicates_by_sha256']}")
        print(f"   Название приложения: {self.metrics['duplicates_by_name']}")
        print(f"   Размер файла: {self.metrics['duplicates_by_size']}")
        
        print(f"\n🔍 ДОПОЛНИТЕЛЬНАЯ СТАТИСТИКА:")
        print(f"   Похожих приложений найдено: {self.metrics['similar_apps_found']}")
        print(f"   Файлов заменено по приоритету: {self.metrics['files_replaced_by_priority']}")
        
        if self.metrics['start_time'] and self.metrics['end_time']:
            duration = (self.metrics['end_time'] - self.metrics['start_time']).total_seconds()
            print(f"\n⏱️ Время обработки: {duration:.2f} секунд")
            if total > 0:
                print(f"⚡ Скорость: {total/duration:.2f} файлов/сек")
        
        print("="*60)
    
    def get_duplicate_statistics(self) -> Dict:
        """Получаем статистику дублей"""
        return {
            'total_duplicates': self.metrics['duplicates_found'],
            'by_type': {
                'sha256': self.metrics['duplicates_by_sha256'],
                'package': self.metrics['duplicates_by_package'],
                'name': self.metrics['duplicates_by_name'],
                'size': self.metrics['duplicates_by_size']
            },
            'similar_apps': self.metrics['similar_apps_found'],
            'replaced_files': self.metrics['files_replaced_by_priority']
        }
