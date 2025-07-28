# Telegram Voice-to-Insight Pipeline Setup Instructions

## 🚀 Quick Setup

### For macOS (recommended method):
```bash
# 0. Install system dependencies (if not already installed)
brew install pkg-config ffmpeg

# 1. Run the enhanced setup script
python3 setup.py

# 2. If you need to manually activate virtual environment:
source venv/bin/activate

# 3. Edit .env with your tokens
cp .env.template .env
# Then edit .env file with your actual TELEGRAM_TOKEN and OPENAI_API_KEY

# 4. Start Redis
docker compose up redis -d

# 5. Run the bot
python3 main.py
```

### For Linux:
```bash
# 1. Run setup script
python3 setup.py

# 2. Edit .env with your tokens
cp .env.template .env
# Then edit .env file with your actual tokens

# 3. Start Redis
docker compose up redis -d

# 4. Run the bot
python3 main.py
```

### For Windows:
```cmd
# 1. Run setup script
python setup.py

# 2. Edit .env with your tokens
copy .env.template .env
# Then edit .env file with your actual tokens

# 3. Start Redis
docker compose up redis -d

# 4. Run the bot
python main.py
```

## 🛠️ Manual Setup (if automated script fails)

### macOS Manual Setup:
```bash
# 0. Install system dependencies
brew install pkg-config ffmpeg

# 1. Create virtual environment (required for macOS due to PEP 668)
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create configuration
cp .env.template .env
# Edit .env with your actual tokens

# 4. Start Redis
docker compose up redis -d

# 5. Run bot
python3 main.py
```

### Linux Manual Setup:
```bash
# 1. Install dependencies
pip3 install -r requirements.txt

# 2. Create configuration  
cp .env.template .env
# Edit .env with your actual tokens

# 3. Start Redis
docker compose up redis -d

# 4. Run bot
python3 main.py
```

## 📋 Required Configuration

Edit your `.env` file with these required values:

1. **TELEGRAM_TOKEN**: Get from [@BotFather](https://t.me/BotFather) on Telegram
2. **OPENAI_API_KEY**: Get from [OpenAI Platform](https://platform.openai.com/api-keys)

## 🔧 Troubleshooting

### macOS: "externally-managed-environment" Error
```bash
# This error occurs due to PEP 668 on macOS
# Solution: Use virtual environment (automated in setup.py)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Python 3.13 Compatibility Issues
```bash
# Some packages (pydantic-core, PyAV) don't support Python 3.13 yet
# For testing basic functionality, use simplified requirements:
pip install -r requirements-basic.txt

# Or install Python 3.11/3.12 for full compatibility:
brew install python@3.11
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Docker Compose Issues
```bash
# If old docker-compose syntax fails, use new syntax:
docker compose up redis -d

# If that fails, try legacy syntax:
docker-compose up redis -d
```

### Permission Issues
```bash
# macOS/Linux: If permission denied
chmod +x setup.py

# Windows: Run as Administrator if needed
```

## ✅ Verification

After setup, verify everything works:

```bash
# Check if bot starts without errors
python3 main.py

# You should see:
# ✅ Configuration loaded successfully
# ✅ Bot started successfully
```

## 📁 Project Structure

After setup, your project should have:
```
FirstProject/
├── venv/                 # Virtual environment (macOS)
├── .env                  # Your configuration
├── .env.template         # Configuration template
├── main.py              # Bot application
├── config.py            # Configuration loader
├── setup.py             # Enhanced setup script
└── requirements.txt     # Dependencies
``` 