# Process Manager - Single Instance Enforcement

## Overview

The Process Manager system ensures that only one instance of the Telegram bot runs at any time, preventing polling conflicts and TelegramConflictError issues.

## Automatic Integration

The process manager is **automatically enabled** when starting the bot:

```bash
python main.py
```

The system will:
1. ✅ Detect any existing main.py processes  
2. ✅ Gracefully terminate duplicate processes (SIGTERM)
3. ✅ Acquire single-instance lock
4. ✅ Start the bot normally
5. ✅ Clean up on shutdown

## Manual Diagnostics

### Check Current Status
```bash
python process_manager.py
```

### Test Process Cleanup
```python
from process_manager import create_process_manager

manager = create_process_manager()
results = manager.terminate_duplicate_processes()
print(f"Terminated: {results['terminated']}")
```

### Manual Single-Instance Enforcement
```python
from process_manager import enforce_single_instance

# This is already integrated in main.py
process_manager = enforce_single_instance(
    auto_cleanup=True,     # Automatically clean up duplicates
    force_cleanup=False    # Use graceful termination first
)
```

## Log Output

Normal startup with process management:
```
INFO - Инициализация single-instance enforcement...
INFO - Проверка single-instance enforcement...
INFO - Найдено 2 дублирующих процессов
INFO - Автоматическая очистка дублирующих процессов...
INFO - Завершение процесса PID 63946 сигналом SIGTERM
INFO - Процесс PID 63946 успешно завершён
INFO - Single-instance enforcement успешно установлен
INFO - ✅ Single-instance enforcement активирован
```

## Files Created

- `.bot_instance.lock` - Lock file (auto-created/removed)
- `.bot_instance.lock.info` - Lock metadata (auto-created/removed)

## Troubleshooting

### Issue: "Cannot acquire lock"
**Solution**: Another instance is running or wasn't cleaned up properly
```bash
# Check for stuck processes
python process_manager.py

# Force cleanup if needed
rm .bot_instance.lock*
```

### Issue: Processes not terminating
**Solution**: Use force cleanup
```python
from process_manager import create_process_manager
manager = create_process_manager()
manager.terminate_duplicate_processes(force=True)  # Uses SIGKILL
```

## Production Benefits

- ✅ **Eliminates TelegramConflictError**: No more polling conflicts
- ✅ **Prevents Resource Waste**: Single bot instance only  
- ✅ **Stable API Interaction**: Consistent Telegram API usage
- ✅ **Automatic Recovery**: Self-healing on process conflicts
- ✅ **Cross-Platform**: Works on macOS, Linux, Windows

## Dependencies

- `psutil==7.0.0` - Process management
- `filelock==3.13.1` - File-based locking

Already included in `requirements.txt`. 