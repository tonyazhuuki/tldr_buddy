# 🔍 MCP Processor Debug Guide - Railway Troubleshooting

## ❌ **Проблема: MCP процессор не инициализируется в Railway**

### **Ошибка пользователя:**
```
❌ YouTube обработка недоступна

Ссылка: https://www.youtube.com/watch?v=1vQ0RpfCqH0

MCP YouTube процессор не инициализирован.
Попробуйте позже или обратитесь к администратору.
```

### **Локальные тесты:**
✅ **Локально все работает:**
```
INFO:__main__:🎉 All MCP debug tests passed!
✅ MCP processor debug completed successfully
```

## 🔍 **Отладка Railway:**

### **1. Добавлено подробное логирование**

#### **В main.py:**
```python
# Initialize MCP YouTube processor
logger.info("Initializing MCP YouTube processor...")
try:
    logger.info("Step 1: Importing create_real_mcp_youtube_processor...")
    from mcp_youtube_real import create_real_mcp_youtube_processor
    logger.info("✅ create_real_mcp_youtube_processor imported successfully")
    
    logger.info("Step 2: Creating MCP YouTube processor...")
    mcp_youtube_processor = create_real_mcp_youtube_processor()
    logger.info(f"✅ MCP YouTube processor created: available={mcp_youtube_processor.available}")
    
    if mcp_youtube_processor.available:
        logger.info("✅ MCP YouTube processor initialized with get_transcript service")
    else:
        logger.warning("⚠️ MCP YouTube processor created but not available")
        
except ImportError as import_error:
    logger.error(f"MCP YouTube processor import failed: {import_error}")
    mcp_youtube_processor = None
except Exception as mcp_error:
    logger.error(f"MCP YouTube processor initialization failed: {mcp_error}")
    logger.exception("Full error details:")
    mcp_youtube_processor = None
```

### **2. Создан отладочный скрипт**

#### **debug_mcp.py:**
```python
def debug_mcp_processor():
    """Debug MCP YouTube processor step by step"""
    
    # Step 1: Check Python version
    logger.info(f"Python version: {sys.version}")
    
    # Step 2: Check if yt-dlp is available
    logger.info("Step 1: Checking yt-dlp availability...")
    try:
        import yt_dlp
        logger.info(f"✅ yt-dlp imported successfully: {yt_dlp.version.__version__}")
    except ImportError as e:
        logger.error(f"❌ yt-dlp import failed: {e}")
        return False
    
    # Step 3: Check if requests is available
    logger.info("Step 2: Checking requests availability...")
    try:
        import requests
        logger.info(f"✅ requests imported successfully: {requests.__version__}")
    except ImportError as e:
        logger.error(f"❌ requests import failed: {e}")
        return False
    
    # Step 4: Check if get_transcript_ytdlp can be imported
    logger.info("Step 3: Checking get_transcript_ytdlp import...")
    try:
        from get_transcript_ytdlp import get_transcript
        logger.info("✅ get_transcript_ytdlp imported successfully")
    except ImportError as e:
        logger.error(f"❌ get_transcript_ytdlp import failed: {e}")
        return False
    
    # Step 5: Check if mcp_youtube_real can be imported
    logger.info("Step 4: Checking mcp_youtube_real import...")
    try:
        from mcp_youtube_real import create_real_mcp_youtube_processor
        logger.info("✅ mcp_youtube_real imported successfully")
    except ImportError as e:
        logger.error(f"❌ mcp_youtube_real import failed: {e}")
        return False
    
    # Step 6: Create MCP processor
    logger.info("Step 5: Creating MCP processor...")
    try:
        mcp_processor = create_real_mcp_youtube_processor()
        logger.info(f"✅ MCP processor created: available={mcp_processor.available}")
        
        if not mcp_processor.available:
            logger.error("❌ MCP processor not available")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to create MCP processor: {e}")
        logger.exception("Full error details:")
        return False
    
    # Step 7: Test video ID extraction
    logger.info("Step 6: Testing video ID extraction...")
    try:
        test_url = "https://www.youtube.com/watch?v=1vQ0RpfCqH0"
        video_id = mcp_processor.extract_video_id(test_url)
        logger.info(f"✅ Video ID extracted: {video_id}")
        
        if video_id != "1vQ0RpfCqH0":
            logger.error(f"❌ Wrong video ID: {video_id}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Video ID extraction failed: {e}")
        return False
    
    logger.info("🎉 All MCP debug tests passed!")
    return True
```

## 🚀 **Статус деплоя:**

### **Исправление отправлено в git:**
- ✅ **Добавлено подробное логирование** - пошаговая отладка
- ✅ **Создан отладочный скрипт** - debug_mcp.py
- ✅ **Локальные тесты проходят** - MCP процессор работает
- ✅ **Railway автоматически подхватит изменения**

### **Ожидаемый результат:**
- **🔄 Статус:** Railway начнет новый деплой
- **⏱️ Время:** 3-5 минут
- **🎯 Цель:** Увидеть подробные логи инициализации MCP

## 🔍 **Мониторинг:**

### **После деплоя проверьте:**

#### **1. Railway Dashboard:**
- Статус должен измениться на "Deployed"

#### **2. Railway Logs:**
Ищите логи инициализации MCP процессора:
```
Initializing MCP YouTube processor...
Step 1: Importing create_real_mcp_youtube_processor...
Step 2: Creating MCP YouTube processor...
```

#### **3. Health Check:**
```
https://your-railway-app.railway.app/health
```

#### **4. Debug Check:**
```
https://your-railway-app.railway.app/debug
```

#### **5. Тестирование YouTube TLDR:**
Отправьте боту: `https://www.youtube.com/watch?v=1vQ0RpfCqH0`

## 📋 **Возможные проблемы:**

### **1. ImportError в Railway:**
```
MCP YouTube processor import failed: No module named 'mcp_youtube_real'
```
**Решение:** Проверить, что файл `mcp_youtube_real.py` существует в Railway

### **2. yt-dlp недоступен:**
```
yt-dlp import failed: No module named 'yt_dlp'
```
**Решение:** Проверить, что `yt-dlp` установлен в Railway

### **3. get_transcript недоступен:**
```
get_transcript_ytdlp import failed: No module named 'get_transcript_ytdlp'
```
**Решение:** Проверить, что файл `get_transcript_ytdlp.py` существует в Railway

### **4. MCP processor not available:**
```
MCP YouTube processor created but not available
```
**Решение:** Проверить логи `mcp_youtube_real.py` для деталей

## 🛠️ **Локальное тестирование:**

### **Запуск отладочного скрипта:**
```bash
python debug_mcp.py
```

### **Ожидаемый результат:**
```
INFO:__main__:🎉 All MCP debug tests passed!
✅ MCP processor debug completed successfully
```

### **Запуск основного теста:**
```bash
python test_mcp.py
```

### **Ожидаемый результат:**
```
INFO:__main__:🎉 All MCP tests passed!
✅ MCP processor is working correctly
```

## 📋 **История исправлений:**

### **Исправление #1 (fd47c03):**
- Исправлены отступы в области строк 1341-1342

### **Исправление #2 (9cf093a):**
- Исправлен отступ на строке 1492

### **Исправление #3 (94ac04c):**
- Системное исправление всех отступов
- Файл компилируется без ошибок

### **Исправление #4 (084877e):**
- Добавлены недостающие зависимости
- psutil, filelock, pytz

### **Исправление #5 (32ffd63):**
- Удалена YouTube API логика
- Только MCP подход

### **Исправление #6 (c297eb3):**
- yt-dlp Python API вместо командной строки
- requests вместо curl
- Railway совместимость

### **Исправление #7 (bb7bda8):** 🎯 **ОТЛАДОЧНОЕ**
- **Добавлено подробное логирование**
- **Создан отладочный скрипт**
- **Пошаговая отладка Railway**

## 🎯 **Ключевые моменты:**

1. **✅ Локально работает** - MCP процессор функционирует
2. **✅ Подробное логирование** - пошаговая отладка
3. **✅ Отладочный скрипт** - тестирование компонентов
4. **✅ Railway совместимость** - должно работать
5. **✅ Диагностика** - выявление проблемы

---

## 🎯 **ИТОГ:**

**🔍 ОТЛАДКА MCP ПРОЦЕССОРА ДОБАВЛЕНА!**

**✅ Подробное логирование инициализации**
**✅ Отладочный скрипт для тестирования**
**✅ Локальные тесты проходят**
**✅ Railway логи покажут проблему!**

**🔧 Исправление отправлено в git и Railway автоматически подхватит изменения!**

**🚀 Ожидайте успешного деплоя через 3-5 минут!**

**🔍 Проверьте Railway логи для выявления проблемы с MCP процессором!** 