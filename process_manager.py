#!/usr/bin/env python3
"""
Process Manager для Telegram Voice-to-Insight Pipeline
Обеспечивает single-instance enforcement и управление процессами
"""

import os
import sys
import time
import signal
import psutil
import logging
import filelock
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class ProcessInfo:
    """Информация о процессе"""
    pid: int
    cmdline: List[str]
    name: str
    create_time: float
    status: str

class ProcessManager:
    """Менеджер процессов для обеспечения single-instance enforcement"""
    
    def __init__(self, app_name: str = "telegram-voice-bot", lock_file: str = ".bot_instance.lock"):
        """
        Инициализация ProcessManager
        
        Args:
            app_name: Название приложения для идентификации процессов
            lock_file: Путь к файлу блокировки
        """
        self.app_name = app_name
        self.lock_file = Path(lock_file).resolve()
        self.logger = logging.getLogger(__name__)
        self.lock = None
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Настройка логирования для ProcessManager"""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def find_duplicate_processes(self, exclude_current: bool = True) -> List[ProcessInfo]:
        """
        Поиск дублирующих процессов main.py
        
        Args:
            exclude_current: Исключить текущий процесс из результатов
            
        Returns:
            Список ProcessInfo с дублирующими процессами
        """
        current_pid = os.getpid()
        duplicate_processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'status']):
                try:
                    proc_info = proc.info
                    cmdline = proc_info.get('cmdline', [])
                    
                    # Проверяем если это процесс main.py
                    if cmdline and any('main.py' in cmd for cmd in cmdline):
                        # Исключаем текущий процесс если нужно
                        if exclude_current and proc_info['pid'] == current_pid:
                            continue
                            
                        process_info = ProcessInfo(
                            pid=proc_info['pid'],
                            cmdline=cmdline,
                            name=proc_info.get('name', 'unknown'),
                            create_time=proc_info.get('create_time', 0),
                            status=proc_info.get('status', 'unknown')
                        )
                        duplicate_processes.append(process_info)
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    # Процесс завершился или нет доступа - пропускаем
                    continue
                    
        except Exception as e:
            self.logger.error(f"Ошибка при поиске дублирующих процессов: {e}")
            
        return duplicate_processes
    
    def terminate_duplicate_processes(self, force: bool = False) -> Dict[str, Any]:
        """
        Завершение дублирующих процессов
        
        Args:
            force: Использовать SIGKILL вместо SIGTERM
            
        Returns:
            Словарь с результатами операции
        """
        results = {
            'found': 0,
            'terminated': 0,
            'failed': 0,
            'processes': []
        }
        
        duplicate_processes = self.find_duplicate_processes(exclude_current=True)
        results['found'] = len(duplicate_processes)
        
        if not duplicate_processes:
            self.logger.info("Дублирующие процессы не найдены")
            return results
        
        self.logger.info(f"Найдено {len(duplicate_processes)} дублирующих процессов")
        
        # Сортируем по времени создания (старые первыми)
        duplicate_processes.sort(key=lambda p: p.create_time)
        
        for process_info in duplicate_processes:
            try:
                proc = psutil.Process(process_info.pid)
                
                # Проверяем что процесс всё ещё существует
                if not proc.is_running():
                    continue
                
                signal_type = signal.SIGKILL if force else signal.SIGTERM
                signal_name = "SIGKILL" if force else "SIGTERM"
                
                self.logger.info(
                    f"Завершение процесса PID {process_info.pid} "
                    f"(создан: {time.ctime(process_info.create_time)}) "
                    f"сигналом {signal_name}"
                )
                
                proc.send_signal(signal_type)
                
                # Ждём завершения процесса (макс. 5 секунд)
                try:
                    proc.wait(timeout=5)
                    results['terminated'] += 1
                    results['processes'].append({
                        'pid': process_info.pid,
                        'status': 'terminated',
                        'signal': signal_name
                    })
                    self.logger.info(f"Процесс PID {process_info.pid} успешно завершён")
                    
                except psutil.TimeoutExpired:
                    if not force:
                        # Если SIGTERM не сработал, пробуем SIGKILL
                        self.logger.warning(
                            f"Процесс PID {process_info.pid} не ответил на SIGTERM, "
                            f"принудительное завершение SIGKILL"
                        )
                        proc.kill()
                        proc.wait(timeout=3)
                        results['terminated'] += 1
                        results['processes'].append({
                            'pid': process_info.pid,
                            'status': 'force_killed',
                            'signal': 'SIGKILL'
                        })
                    else:
                        results['failed'] += 1
                        results['processes'].append({
                            'pid': process_info.pid,
                            'status': 'timeout',
                            'signal': signal_name
                        })
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                self.logger.warning(f"Не удалось завершить процесс PID {process_info.pid}: {e}")
                results['failed'] += 1
                results['processes'].append({
                    'pid': process_info.pid,
                    'status': 'failed',
                    'error': str(e)
                })
            except Exception as e:
                self.logger.error(f"Неожиданная ошибка при завершении процесса PID {process_info.pid}: {e}")
                results['failed'] += 1
                results['processes'].append({
                    'pid': process_info.pid,
                    'status': 'error',
                    'error': str(e)
                })
        
        self.logger.info(
            f"Завершение процессов: {results['terminated']} успешно, "
            f"{results['failed']} неудачно из {results['found']} найденных"
        )
        
        return results
    
    def acquire_lock(self, timeout: float = 5.0) -> bool:
        """
        Получение блокировки для single-instance enforcement
        
        Args:
            timeout: Таймаут для получения блокировки в секундах
            
        Returns:
            True если блокировка получена, False если не удалось
        """
        try:
            self.lock = filelock.FileLock(str(self.lock_file), timeout=timeout)
            self.lock.acquire()
            
            # Записываем PID в файл блокировки для отладки
            lock_info = {
                'pid': os.getpid(),
                'timestamp': time.time(),
                'app_name': self.app_name
            }
            
            with open(str(self.lock_file) + '.info', 'w') as f:
                import json
                json.dump(lock_info, f, indent=2)
            
            self.logger.info(f"Блокировка получена: {self.lock_file}")
            return True
            
        except filelock.Timeout:
            self.logger.error(f"Не удалось получить блокировку в течение {timeout}s: {self.lock_file}")
            return False
        except Exception as e:
            self.logger.error(f"Ошибка при получении блокировки: {e}")
            return False
    
    def release_lock(self) -> None:
        """Освобождение блокировки"""
        if self.lock:
            try:
                self.lock.release()
                # Удаляем info файл
                info_file = Path(str(self.lock_file) + '.info')
                if info_file.exists():
                    info_file.unlink()
                self.logger.info(f"Блокировка освобождена: {self.lock_file}")
            except Exception as e:
                self.logger.error(f"Ошибка при освобождении блокировки: {e}")
            finally:
                self.lock = None
    
    def enforce_single_instance(self, auto_cleanup: bool = True, force_cleanup: bool = False) -> bool:
        """
        Обеспечение single-instance режима
        
        Args:
            auto_cleanup: Автоматически завершать дублирующие процессы
            force_cleanup: Использовать принудительное завершение (SIGKILL)
            
        Returns:
            True если single-instance обеспечен, False если есть конфликты
        """
        self.logger.info("Проверка single-instance enforcement...")
        
        # Сначала проверяем дублирующие процессы
        duplicate_processes = self.find_duplicate_processes(exclude_current=True)
        
        if duplicate_processes:
            self.logger.warning(f"Найдено {len(duplicate_processes)} дублирующих процессов")
            
            if auto_cleanup:
                self.logger.info("Автоматическая очистка дублирующих процессов...")
                cleanup_results = self.terminate_duplicate_processes(force=force_cleanup)
                
                if cleanup_results['failed'] > 0:
                    self.logger.error(
                        f"Не удалось завершить {cleanup_results['failed']} процессов. "
                        f"Single-instance не может быть обеспечен."
                    )
                    return False
                
                # Даём время на завершение процессов
                time.sleep(1)
                
                # Проверяем ещё раз
                remaining_processes = self.find_duplicate_processes(exclude_current=True)
                if remaining_processes:
                    self.logger.error(f"Остались активные дублирующие процессы: {len(remaining_processes)}")
                    return False
            else:
                self.logger.error("Auto cleanup отключён. Single-instance не может быть обеспечен.")
                return False
        
        # Пытаемся получить блокировку
        if not self.acquire_lock():
            self.logger.error("Не удалось получить блокировку single-instance")
            return False
        
        self.logger.info("Single-instance enforcement успешно установлен")
        return True
    
    def setup_signal_handlers(self) -> None:
        """Настройка обработчиков сигналов для корректного завершения"""
        def signal_handler(signum, frame):
            signal_name = signal.Signals(signum).name
            self.logger.info(f"Получен сигнал {signal_name}, корректное завершение...")
            self.release_lock()
            sys.exit(0)
        
        # Регистрируем обработчики для SIGTERM и SIGINT
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        self.logger.info("Обработчики сигналов настроены")
    
    def get_status_report(self) -> Dict[str, Any]:
        """
        Получение отчёта о состоянии process management
        
        Returns:
            Словарь с информацией о состоянии
        """
        duplicate_processes = self.find_duplicate_processes(exclude_current=True)
        lock_status = self.lock is not None and self.lock.is_locked
        
        return {
            'current_pid': os.getpid(),
            'lock_file': str(self.lock_file),
            'lock_acquired': lock_status,
            'duplicate_processes_count': len(duplicate_processes),
            'duplicate_processes': [
                {
                    'pid': p.pid,
                    'cmdline': ' '.join(p.cmdline),
                    'create_time': time.ctime(p.create_time),
                    'status': p.status
                }
                for p in duplicate_processes
            ],
            'single_instance_enforced': lock_status and len(duplicate_processes) == 0
        }

def create_process_manager(app_name: str = "telegram-voice-bot") -> ProcessManager:
    """
    Factory function для создания ProcessManager
    
    Args:
        app_name: Название приложения
        
    Returns:
        Настроенный ProcessManager
    """
    return ProcessManager(app_name=app_name)

# Утилитарные функции для быстрого использования

def enforce_single_instance(auto_cleanup: bool = True, force_cleanup: bool = False) -> ProcessManager:
    """
    Быстрое обеспечение single-instance режима
    
    Args:
        auto_cleanup: Автоматически завершать дублирующие процессы
        force_cleanup: Использовать принудительное завершение
        
    Returns:
        ProcessManager если успешно, иначе вызывает SystemExit
    """
    manager = create_process_manager()
    manager.setup_signal_handlers()
    
    if not manager.enforce_single_instance(auto_cleanup=auto_cleanup, force_cleanup=force_cleanup):
        manager.logger.error("КРИТИЧЕСКАЯ ОШИБКА: Не удалось обеспечить single-instance режим")
        manager.logger.error("Возможные причины:")
        manager.logger.error("1. Другой экземпляр бота уже запущен")
        manager.logger.error("2. Процессы-зомби не завершились")
        manager.logger.error("3. Нет прав для завершения процессов")
        manager.logger.error("Остановка приложения...")
        sys.exit(1)
    
    return manager

if __name__ == "__main__":
    # Тестирование и диагностика
    print("=== PROCESS MANAGER DIAGNOSTIC ===")
    
    manager = create_process_manager()
    status = manager.get_status_report()
    
    print(f"Current PID: {status['current_pid']}")
    print(f"Lock file: {status['lock_file']}")
    print(f"Duplicate processes: {status['duplicate_processes_count']}")
    
    if status['duplicate_processes']:
        print("\nДублирующие процессы:")
        for proc in status['duplicate_processes']:
            print(f"  PID {proc['pid']}: {proc['cmdline']}")
            print(f"    Создан: {proc['create_time']}")
            print(f"    Статус: {proc['status']}")
    
    print(f"\nSingle instance enforced: {status['single_instance_enforced']}") 