#!/usr/bin/env python3
"""
Скрипт для мониторинга производительности бота
"""
import re
import sys
from datetime import datetime, timedelta
from collections import defaultdict, Counter

def analyze_log_performance(log_file_path: str, hours_back: int = 24):
    """
    Анализирует производительность из логов бота
    
    Args:
        log_file_path: Путь к файлу логов
        hours_back: Количество часов назад для анализа
    """
    
    # Паттерны для поиска
    duration_pattern = r'Update id=(\d+) is handled\. Duration (\d+) ms'
    slow_operation_pattern = r'SLOW OPERATION: (.+) took ([\d.]+)ms'
    slow_db_pattern = r'SLOW DB OPERATION: (.+) took ([\d.]+)ms'
    slow_message_pattern = r'SLOW MESSAGE PROCESSING: message_id=(\d+), user_id=(\d+), handler=(.+), duration=([\d.]+)ms'
    
    # Статистика
    update_durations = []
    slow_operations = []
    slow_db_operations = []
    slow_messages = []
    
    # Временной фильтр
    cutoff_time = datetime.now() - timedelta(hours=hours_back)
    
    print(f"🔍 Анализ производительности за последние {hours_back} часов...")
    print(f"📅 С {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    # Извлекаем время из лога
                    time_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                    if time_match:
                        log_time = datetime.strptime(time_match.group(1), '%Y-%m-%d %H:%M:%S')
                        if log_time < cutoff_time:
                            continue
                    
                    # Анализ времени обработки апдейтов
                    duration_match = re.search(duration_pattern, line)
                    if duration_match:
                        update_id, duration = duration_match.groups()
                        update_durations.append(int(duration))
                    
                    # Анализ медленных операций
                    slow_op_match = re.search(slow_operation_pattern, line)
                    if slow_op_match:
                        operation, duration = slow_op_match.groups()
                        slow_operations.append((operation, float(duration)))
                    
                    # Анализ медленных БД операций
                    slow_db_match = re.search(slow_db_pattern, line)
                    if slow_db_match:
                        operation, duration = slow_db_match.groups()
                        slow_db_operations.append((operation, float(duration)))
                    
                    # Анализ медленных сообщений
                    slow_msg_match = re.search(slow_message_pattern, line)
                    if slow_msg_match:
                        msg_id, user_id, handler, duration = slow_msg_match.groups()
                        slow_messages.append((int(msg_id), int(user_id), handler, float(duration)))
                
                except Exception as e:
                    print(f"⚠️ Ошибка обработки строки {line_num}: {e}")
                    continue
    
    except FileNotFoundError:
        print(f"❌ Файл логов не найден: {log_file_path}")
        return
    except Exception as e:
        print(f"❌ Ошибка чтения логов: {e}")
        return
    
    # Анализ результатов
    if not update_durations:
        print("📊 Нет данных о времени обработки апдейтов")
        return
    
    # Статистика по времени обработки
    print("📊 СТАТИСТИКА ВРЕМЕНИ ОБРАБОТКИ:")
    print(f"   Всего апдейтов: {len(update_durations)}")
    print(f"   Среднее время: {sum(update_durations) / len(update_durations):.1f}ms")
    print(f"   Медиана: {sorted(update_durations)[len(update_durations)//2]}ms")
    print(f"   Минимум: {min(update_durations)}ms")
    print(f"   Максимум: {max(update_durations)}ms")
    
    # Медленные апдейты
    slow_updates = [d for d in update_durations if d > 500]
    very_slow_updates = [d for d in update_durations if d > 1000]
    
    print(f"\n🐌 МЕДЛЕННЫЕ ОБРАБОТКИ:")
    print(f"   > 500ms: {len(slow_updates)} ({len(slow_updates)/len(update_durations)*100:.1f}%)")
    print(f"   > 1000ms: {len(very_slow_updates)} ({len(very_slow_updates)/len(update_durations)*100:.1f}%)")
    
    if very_slow_updates:
        print(f"   Самые медленные: {sorted(very_slow_updates, reverse=True)[:5]}ms")
    
    # Анализ медленных операций
    if slow_operations:
        print(f"\n🔧 МЕДЛЕННЫЕ ОПЕРАЦИИ ({len(slow_operations)}):")
        operation_stats = defaultdict(list)
        for op, duration in slow_operations:
            operation_stats[op].append(duration)
        
        for op, durations in sorted(operation_stats.items(), key=lambda x: max(x[1]), reverse=True):
            print(f"   {op}: {len(durations)} раз, макс: {max(durations):.1f}ms, среднее: {sum(durations)/len(durations):.1f}ms")
    
    # Анализ медленных БД операций
    if slow_db_operations:
        print(f"\n🗄️ МЕДЛЕННЫЕ БД ОПЕРАЦИИ ({len(slow_db_operations)}):")
        db_stats = defaultdict(list)
        for op, duration in slow_db_operations:
            db_stats[op].append(duration)
        
        for op, durations in sorted(db_stats.items(), key=lambda x: max(x[1]), reverse=True):
            print(f"   {op}: {len(durations)} раз, макс: {max(durations):.1f}ms, среднее: {sum(durations)/len(durations):.1f}ms")
    
    # Анализ медленных сообщений
    if slow_messages:
        print(f"\n💬 МЕДЛЕННЫЕ СООБЩЕНИЯ ({len(slow_messages)}):")
        handler_stats = defaultdict(list)
        for msg_id, user_id, handler, duration in slow_messages:
            handler_stats[handler].append(duration)
        
        for handler, durations in sorted(handler_stats.items(), key=lambda x: max(x[1]), reverse=True):
            print(f"   {handler}: {len(durations)} раз, макс: {max(durations):.1f}ms, среднее: {sum(durations)/len(durations):.1f}ms")
    
    # Рекомендации
    print(f"\n💡 РЕКОМЕНДАЦИИ:")
    
    if len(very_slow_updates) / len(update_durations) > 0.05:  # >5% очень медленных
        print("   ⚠️ КРИТИЧНО: Слишком много очень медленных обработок (>1000ms)")
        print("   🔧 Рекомендуется оптимизировать AliasService и БД операции")
    
    if len(slow_updates) / len(update_durations) > 0.2:  # >20% медленных
        print("   ⚠️ ВНИМАНИЕ: Много медленных обработок (>500ms)")
        print("   🔧 Рекомендуется добавить кэширование и оптимизировать запросы")
    
    if slow_db_operations:
        print("   🗄️ Оптимизируйте операции с базой данных")
        print("   📊 Добавьте индексы и connection pooling")
    
    if slow_operations:
        print("   ⚡ Оптимизируйте медленные операции")
        print("   🚀 Рассмотрите асинхронную обработку")

def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("Использование: python performance_monitor.py <путь_к_логам> [часов_назад]")
        print("Пример: python performance_monitor.py bot.log 24")
        sys.exit(1)
    
    log_file = sys.argv[1]
    hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    
    analyze_log_performance(log_file, hours)

if __name__ == "__main__":
    main()
