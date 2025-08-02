#!/usr/bin/env python3
"""
Скрипт для пакетной конвертации TIFF в WebP Lossless с максимальным сжатием

Логика работы:
1. Определение целевых каталогов для обработки:
   - Без аргументов: сканирует текущий каталог на наличие подкаталогов с TIFF-файлами
   - С аргументом-каталогом: обрабатывает указанный каталог
   - С аргументом-TXT-файлом: обрабатывает каталоги из списка в файле
2. Для каждого каталога:
   - Создает соответствующий каталог с суффиксом _webp (или в указанной выходной директории)
   - Определяет TIFF-файлы, которые еще не конвертированы
   - Последовательно конвертирует файлы (1 поток для минимизации нагрузки на HDD)
3. Сбор статистики:
   - Время обработки каждого файла
   - Коэффициенты сжатия
   - Общая экономия места
4. Формирование подробного отчета по завершении
"""

import os
import sys
import argparse
import logging
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

def setup_logger():
    """Настройка системы логирования
    
    Создает логгер с:
    - Выводом в консоль
    - Записью в файл tiff2webp.log
    - Форматированием с временными метками
    """
    logger = logging.getLogger('tiff2webp')
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', 
                                  datefmt='%Y-%m-%d %H:%M:%S')
    
    # Обработчик для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Обработчик для записи в файл
    file_handler = logging.FileHandler('tiff2webp.log')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

def find_tiff_dirs(root_path):
    """Поиск каталогов, содержащих TIFF-файлы
    
    Аргументы:
        root_path: Путь для начала поиска
        
    Возвращает:
        Список путей к каталогам, содержащим файлы .tif или .tiff
    """
    tiff_dirs = []
    
    for entry in os.scandir(root_path):
        if not entry.is_dir():
            continue  # Пропускаем файлы
        
        # Проверка наличия TIFF-файлов в каталоге
        has_tiff = False
        for file_entry in os.scandir(entry.path):
            if file_entry.is_file() and file_entry.name.lower().endswith(('.tif', '.tiff')):
                has_tiff = True
                break  # Прекращаем при первом найденном TIFF
        
        if has_tiff:
            tiff_dirs.append(entry.path)
    
    return tiff_dirs

def convert_to_webp(input_path, output_path):
    """Конвертация одного TIFF-файла в WebP с максимальным сжатием
    
    Аргументы:
        input_path: Путь к исходному TIFF-файлу
        output_path: Путь для сохранения WebP-файла
        
    Возвращает:
        (success, elapsed): 
            success - Флаг успешности операции
            elapsed - Время выполнения в секундах
    """
    try:
        # Команда для максимального сжатия
        cmd = [
            'cwebp',
            '-lossless',    # Режим без потерь
            '-quiet',       # Отключение лишнего вывода
            '-m', '6',      # Максимальный метод сжатия (0-6)
            '-z', '9',      # Максимальный уровень усилий (0-9)
            '-pass', '10',  # Максимальное количество проходов
            input_path,
            '-o', output_path
        ]
        
        start_time = time.time()
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        elapsed = time.time() - start_time
        
        return (True, elapsed) if result.returncode == 0 else (False, 0)
    except Exception as e:
        logger.error(f"Ошибка конвертации {input_path}: {str(e)}")
        return False, 0

def process_directory(tiff_dir, output_root=None, force_convert=False):
    """Обработка каталога с TIFF-файлами
    
    Аргументы:
        tiff_dir: Путь к каталогу с TIFF-файлами
        output_root: Корневая директория для сохранения (None для суффикса _webp)
        force_convert: Флаг принудительной конвертации всех файлов
        
    Возвращает:
        (success_count, total_time, avg_ratio, total_orig, total_compressed)
            success_count: Количество успешно сконвертированных файлов
            total_time: Суммарное время конвертации (секунды)
            avg_ratio: Средний коэффициент сжатия
            total_orig: Суммарный размер исходных файлов (байты)
            total_compressed: Суммарный размер сконвертированных файлов (байты)
    """
    # Определяем путь для сохранения
    base_name = os.path.basename(tiff_dir) + '_webp'  # Всегда добавляем суффикс
    
    if output_root:
        # Создаем путь в указанной выходной директории
        webp_dir = os.path.join(output_root, base_name)
    else:
        # Используем суффикс _webp рядом с исходным каталогом
        webp_dir = os.path.join(os.path.dirname(tiff_dir), base_name)
    
    # Создаем целевой каталог
    os.makedirs(webp_dir, exist_ok=True)
    
    # Получаем список TIFF-файлов
    tiff_files = [
        f.path for f in os.scandir(tiff_dir) 
        if f.is_file() and f.name.lower().endswith(('.tif', '.tiff'))
    ]
    
    # Фильтрация уже конвертированных файлов
    if force_convert:
        files_to_convert = tiff_files
    else:
        # Получаем имена сконвертированных файлов (без расширений)
        converted = {
            os.path.splitext(f.name)[0] 
            for f in os.scandir(webp_dir) 
            if f.is_file() and f.name.lower().endswith('.webp')
        }
        # Оставляем только файлы, которых нет в сконвертированных
        files_to_convert = [
            f for f in tiff_files 
            if os.path.splitext(os.path.basename(f))[0] not in converted
        ]
    
    # Если файлов для конвертации нет - возвращаем нули
    if not files_to_convert:
        return 0, 0, 0, 0, 0
    
    # Инициализация статистики
    total_time = 0
    success_count = 0
    file_sizes = []  # (orig_size, new_size, ratio)
    
    # Прогресс-бар для визуализации процесса
    with tqdm(total=len(files_to_convert), desc=f"Конвертация {os.path.basename(tiff_dir)}") as pbar:
        for tiff_path in files_to_convert:
            # Формируем путь для выходного файла
            file_name = os.path.splitext(os.path.basename(tiff_path))[0] + '.webp'
            output_path = os.path.join(webp_dir, file_name)
            
            # Получаем размер исходного файла
            orig_size = os.path.getsize(tiff_path)
            
            # Выполняем конвертацию
            success, elapsed = convert_to_webp(tiff_path, output_path)
            
            if success:
                # Получаем размер сконвертированного файла
                new_size = os.path.getsize(output_path)
                compression_ratio = new_size / orig_size
                
                # Обновляем статистику
                file_sizes.append((orig_size, new_size, compression_ratio))
                total_time += elapsed
                success_count += 1
                
                # Обновляем информацию в прогресс-баре
                pbar.set_postfix(
                    ratio=f"{compression_ratio:.1%}", 
                    speed=f"{elapsed:.1f}s"
                )
            pbar.update(1)
    
    # Расчет итоговой статистики для каталога
    if file_sizes:
        avg_ratio = sum(r for _, _, r in file_sizes) / len(file_sizes)
        total_orig = sum(s for s, _, _ in file_sizes)
        total_compressed = sum(s for _, s, _ in file_sizes)
    else:
        avg_ratio, total_orig, total_compressed = 0, 0, 0
    
    return success_count, total_time, avg_ratio, total_orig, total_compressed

def format_time(seconds):
    """Форматирование времени в ЧЧ:ММ:СС.ссс
    
    Аргументы:
        seconds: Время в секундах
        
    Возвращает:
        Строка в формате ЧЧ:ММ:СС.ссс
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"

def format_avg_time(seconds):
    """Форматирование времени для отображения средних значений
    
    Аргументы:
        seconds: Время в секундах
        
    Возвращает:
        Строка в формате:
        - X.XXX сек (если < 60 секунд)
        - X мин Y.YYY сек (если > 60 секунд)
    """
    if seconds < 60:
        return f"{seconds:.3f} сек"
    minutes = int(seconds // 60)
    seconds = seconds % 60
    return f"{minutes} мин {seconds:.3f} сек"

def main():
    """Главная функция управления процессом конвертации"""
    start_time = time.time()
    total_files = 0
    total_time = 0
    total_orig_size = 0
    total_compressed_size = 0
    
    # Парсинг аргументов командной строки
    args = parser.parse_args()
    
    # Создаем выходную директорию, если она указана и не существует
    if args.output_dir and not os.path.exists(args.output_dir):
        try:
            os.makedirs(args.output_dir, exist_ok=True)
            logger.info(f"Создана выходная директория: {args.output_dir}")
        except Exception as e:
            logger.error(f"Ошибка создания выходной директории: {str(e)}")
            sys.exit(1)
    
    # Определение режима работы
    if args.target:
        if os.path.isdir(args.target):
            # Режим обработки одного каталога
            count, time_spent, ratio, orig, comp = process_directory(
                args.target, 
                output_root=args.output_dir,
                force_convert=True
            )
            total_files += count
            total_time += time_spent
            total_orig_size += orig
            total_compressed_size += comp
        elif os.path.isfile(args.target) and args.target.endswith('.txt'):
            # Режим обработки списка каталогов из файла
            with open(args.target, 'r') as f:
                directories = [line.strip() for line in f if line.strip()]
            
            for directory in directories:
                if os.path.isdir(directory):
                    count, time_spent, ratio, orig, comp = process_directory(
                        directory, 
                        output_root=args.output_dir,
                        force_convert=False
                    )
                    total_files += count
                    total_time += time_spent
                    total_orig_size += orig
                    total_compressed_size += comp
                else:
                    logger.error(f"Каталог не найден: {directory}")
        else:
            logger.error("Неподдерживаемый тип аргумента. Должен быть каталог или .txt файл")
            sys.exit(1)
    else:
        # Режим сканирования текущего каталога
        logger.info("Сканирование текущего каталога на наличие каталогов с TIFF...")
        tiff_dirs = find_tiff_dirs(os.getcwd())
        
        for directory in tiff_dirs:
            count, time_spent, ratio, orig, comp = process_directory(
                directory, 
                output_root=args.output_dir,
                force_convert=False
            )
            total_files += count
            total_time += time_spent
            total_orig_size += orig
            total_compressed_size += comp
    
    # Расчет итоговой статистики
    total_elapsed = time.time() - start_time
    avg_file_time = total_time / total_files if total_files else 0
    compression_ratio = total_compressed_size / total_orig_size if total_orig_size else 0
    
    # Форматирование и вывод статистики
    logger.info("\n" + "=" * 60)
    logger.info("ОБЩАЯ СТАТИСТИКА КОНВЕРТАЦИИ")
    logger.info(f"Всего обработано файлов: {total_files}")
    logger.info(f"Общее время выполнения: {format_time(total_elapsed)}")
    logger.info(f"Чистое время конвертации: {format_time(total_time)}")
    logger.info(f"Среднее время на файл: {format_avg_time(avg_file_time)}")
    logger.info(f"Общий размер исходных TIFF: {total_orig_size / (1024**2):.2f} МБ")
    logger.info(f"Общий размер WebP: {total_compressed_size / (1024**2):.2f} МБ")
    logger.info(f"Средний коэффициент сжатия: {compression_ratio:.2%}")
    logger.info(f"Экономия места: {(total_orig_size - total_compressed_size) / (1024**2):.2f} МБ")
    logger.info("=" * 60)

if __name__ == "__main__":
    # Инициализация парсера аргументов
    parser = argparse.ArgumentParser(
        description='Оптимизированная конвертация TIFF в WebP Lossless с максимальным сжатием'
    )
    parser.add_argument(
        'target', 
        nargs='?', 
        default=None, 
        help='Путь к каталогу для обработки или TXT-файлу со списком каталогов'
    )
    parser.add_argument(
        '-o', '--output_dir',
        type=str,
        default=None,
        help='Корневая директория для сохранения сконвертированных файлов'
    )
    
    # Инициализация логгера и запуск
    logger = setup_logger()
    try:
        main()
    except Exception as e:
        logger.exception("Критическая ошибка выполнения")
        sys.exit(1)