#!/usr/bin/env python3
"""
Setup script for Telegram Voice-to-Insight Pipeline
Development environment initialization with cross-platform support
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


def detect_platform():
    """Detect operating system and return platform-specific settings"""
    system = platform.system().lower()
    
    platform_info = {
        'system': system,
        'is_macos': system == 'darwin',
        'is_windows': system == 'windows',
        'is_linux': system == 'linux',
        'python_cmd': 'python3' if system != 'windows' else 'python',
        'pip_cmd': 'pip3' if system != 'windows' else 'pip',
        'venv_cmd': [sys.executable, '-m', 'venv']
    }
    
    print(f"🖥️ Detected platform: {system}")
    return platform_info


def check_virtual_environment():
    """Check if we're in a virtual environment"""
    return hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )


def create_virtual_environment(platform_info):
    """Create virtual environment if not exists and not in one"""
    venv_path = Path("venv")
    
    # Check if already in virtual environment
    if check_virtual_environment():
        print("✅ Already running in virtual environment")
        return True, None
    
    # Check if virtual environment already exists
    if venv_path.exists():
        print("✅ Virtual environment already exists")
        return True, venv_path
    
    # Create virtual environment
    print("🔧 Creating virtual environment...")
    try:
        subprocess.run(platform_info['venv_cmd'] + ['venv'], check=True)
        print("✅ Virtual environment created successfully")
        return True, venv_path
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create virtual environment: {e}")
        return False, None


def get_venv_activation_command(platform_info, venv_path):
    """Get platform-specific virtual environment activation command"""
    if not venv_path:
        return None
    
    if platform_info['is_windows']:
        return str(venv_path / "Scripts" / "activate.bat")
    else:
        return f"source {venv_path}/bin/activate"


def run_command(command: list, description: str, platform_info=None):
    """Run a system command with error handling"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else str(e)
        
        # Special handling for macOS PEP 668 error
        if platform_info and platform_info['is_macos'] and 'externally-managed-environment' in error_msg:
            print(f"❌ {description} failed: macOS externally-managed-environment detected")
            print("💡 This requires a virtual environment on macOS")
            return False
        
        print(f"❌ {description} failed: {error_msg}")
        return False


def create_directories():
    """Create necessary project directories"""
    print("📁 Creating project directories...")
    directories = ["temp", "logs", "modes"]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"   ✓ {directory}/")
    
    print("✅ Directory structure created")


def check_system_dependencies(platform_info):
    """Check and suggest installation of system dependencies"""
    print("🔍 Checking system dependencies...")
    
    missing_deps = []
    suggestions = []
    
    if platform_info['is_macos']:
        # Check for pkg-config (required for PyAV/ffmpeg-python)
        try:
            subprocess.run(["pkg-config", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing_deps.append("pkg-config")
            suggestions.append("brew install pkg-config")
        
        # Check for ffmpeg
        try:
            subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing_deps.append("ffmpeg")
            suggestions.append("brew install ffmpeg")
    
    elif platform_info['is_linux']:
        # Check for pkg-config
        try:
            subprocess.run(["pkg-config", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing_deps.append("pkg-config")
            suggestions.append("sudo apt-get install pkg-config")
        
        # Check for ffmpeg
        try:
            subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing_deps.append("ffmpeg")
            suggestions.append("sudo apt-get install ffmpeg")
    
    if missing_deps:
        print(f"⚠️ Missing system dependencies: {', '.join(missing_deps)}")
        print("💡 Install them with:")
        for suggestion in suggestions:
            print(f"   {suggestion}")
        return False
    else:
        print("✅ System dependencies available")
        return True


def install_dependencies(platform_info, venv_path=None):
    """Install Python dependencies with virtual environment support"""
    if not Path("requirements.txt").exists():
        print("❌ requirements.txt not found")
        return False
    
    # Check system dependencies first
    system_deps_ok = check_system_dependencies(platform_info)
    
    print("📦 Installing Python dependencies...")
    print("   This may take a few minutes...")
    
    # Determine pip command
    if venv_path and not check_virtual_environment():
        # Use virtual environment pip
        if platform_info['is_windows']:
            pip_cmd = [str(venv_path / "Scripts" / "pip")]
        else:
            pip_cmd = [str(venv_path / "bin" / "pip")]
    else:
        # Use current environment pip
        pip_cmd = [sys.executable, "-m", "pip"]
    
    # Try to install dependencies
    success = run_command(
        pip_cmd + ["install", "-r", "requirements.txt"],
        "Installing dependencies",
        platform_info
    )
    
    # Handle specific error cases
    if not success:
        if platform_info['is_macos'] and not venv_path:
            print("\n💡 macOS users: If you see 'externally-managed-environment' error:")
            print("   This is due to PEP 668 restrictions on macOS")
            print("   The script will automatically create a virtual environment")
            return False
        elif not system_deps_ok:
            print("\n💡 If you see build errors for ffmpeg-python or PyAV:")
            print("   Install the suggested system dependencies above and retry")
            return False
    
    if success:
        print("✅ All Python dependencies installed")
    
    return success


def create_env_template():
    """Create .env template if it doesn't exist"""
    env_path = Path(".env")
    
    if env_path.exists():
        print("✅ .env file already exists")
        return True
    
    print("📝 Creating .env template...")
    env_template = """# Telegram Voice-to-Insight Pipeline Configuration

# Required: Telegram Bot Token (get from @BotFather)
TELEGRAM_TOKEN=your_telegram_bot_token_here

# Required: OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_MAX_MEMORY=256mb

# Optional: Processing Configuration
MAX_FILE_SIZE=52428800
DEFAULT_TTL=86400
MAX_PROCESSING_TIME=30

# Optional: Whisper Configuration
WHISPER_MODEL=base
WHISPER_DEVICE=cpu

# Optional: Rate Limiting
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_BURST=3
ADMIN_UNLIMITED=false

# Optional: Logging
LOG_LEVEL=INFO

# Optional: Text Processing
CHUNK_SIZE=3000
CHUNK_OVERLAP=500
LANGUAGE_THRESHOLD=0.3

# Optional: Retry Configuration
RETRY_BASE_DELAY=1
RETRY_MAX_ATTEMPTS=3
RETRY_JITTER_PERCENT=0.3
"""
    
    try:
        env_path.write_text(env_template.strip())
        print("✅ .env template created")
        print("📝 Please edit .env file with your actual tokens")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env template: {e}")
        return False


def validate_docker():
    """Validate Docker installation"""
    print("🐳 Checking Docker installation...")
    
    # Check Docker
    docker_ok = run_command(["docker", "--version"], "Checking Docker")
    
    # Check Docker Compose
    compose_ok = run_command(["docker", "compose", "version"], "Checking Docker Compose")
    
    # Fallback to older docker-compose syntax
    if not compose_ok:
        compose_ok = run_command(["docker-compose", "--version"], "Checking Docker Compose (legacy)")
    
    if docker_ok and compose_ok:
        print("✅ Docker environment validated")
        return True
    else:
        print("❌ Docker environment not properly configured")
        return False


def test_configuration():
    """Test configuration loading"""
    print("🧪 Testing configuration...")
    
    try:
        # Test config loading without actual tokens
        import config
        print("✅ Configuration module syntax valid")
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


def print_setup_instructions(platform_info, venv_path):
    """Print platform-specific setup instructions"""
    print("\n📝 Next steps:")
    print("1. Edit .env file with your actual tokens")
    
    if venv_path and not check_virtual_environment():
        activation_cmd = get_venv_activation_command(platform_info, venv_path)
        print(f"2. Activate virtual environment: {activation_cmd}")
        print("3. Start Redis: docker compose up redis -d")
        print("4. Run bot: python main.py")
    else:
        print("2. Start Redis: docker compose up redis -d")
        print("3. Run bot: python main.py")
    
    # Platform-specific notes
    if platform_info['is_macos']:
        print("\n🍎 macOS Notes:")
        print("   - Virtual environment created due to PEP 668 restrictions")
        print("   - Always activate venv before running commands")
        if venv_path:
            print(f"   - Activation command: source {venv_path}/bin/activate")


def main():
    """Main setup function"""
    print("🚀 Telegram Voice-to-Insight Pipeline Setup")
    print("=" * 50)
    
    # Detect platform first
    platform_info = detect_platform()
    
    success_count = 0
    total_steps = 7  # Increased from 6 to 7
    venv_path = None
    
    # Step 1: Create directories
    create_directories()
    success_count += 1
    
    # Step 2: Create virtual environment (new step for macOS compatibility)
    venv_success, venv_path = create_virtual_environment(platform_info)
    if venv_success:
        success_count += 1
    
    # Step 3: Create .env template
    if create_env_template():
        success_count += 1
    
    # Step 4: Validate Docker
    if validate_docker():
        success_count += 1
    
    # Step 5: Install dependencies (with virtual environment support)
    dep_success = install_dependencies(platform_info, venv_path)
    
    # If dependency installation failed on macOS due to PEP 668, retry with venv
    if not dep_success and platform_info['is_macos'] and not venv_path:
        print("\n🔄 Retrying dependency installation with virtual environment...")
        venv_success, venv_path = create_virtual_environment(platform_info)
        if venv_success:
            dep_success = install_dependencies(platform_info, venv_path)
    
    if dep_success:
        success_count += 1
    
    # Step 6: Test configuration
    if test_configuration():
        success_count += 1
    
    # Step 7: Final validation
    print("🔍 Final validation...")
    if Path("main.py").exists() and Path("config.py").exists():
        print("✅ Core application files present")
        success_count += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Setup Results: {success_count}/{total_steps} steps completed")
    
    if success_count == total_steps:
        print("🎉 Setup completed successfully!")
        print_setup_instructions(platform_info, venv_path)
    else:
        print("⚠️ Setup completed with issues")
        print("Please resolve the failed steps before running the bot")
        
        # Provide specific guidance for common issues
        if not dep_success and platform_info['is_macos']:
            print("\n💡 macOS Troubleshooting:")
            print("   If dependencies failed to install, try:")
            print("   1. python3 -m venv venv")
            print("   2. source venv/bin/activate") 
            print("   3. pip install -r requirements.txt")
    
    return success_count == total_steps


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed with unexpected error: {e}")
        sys.exit(1) 