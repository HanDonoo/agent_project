"""
Configuration file for EC Skills Finder API
"""
import os
from pathlib import Path

# Database
DB_PATH = "data/employee_directory_200_mock.db"

# AI Model Configuration
# Options: "ollama" or "gemini"
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")  # 默认使用 Gemini
#AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama")  # 默认使用 Gemini

# Ollama Configuration (if using Ollama)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

# Gemini Configuration (if using Gemini)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")  # 从环境变量读取
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")  # 或 gemini-1.5-flash

# Server Configuration
API_PORT = int(os.getenv("API_PORT", "8001"))
API_HOST = os.getenv("API_HOST", "0.0.0.0")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def validate_config():
    """Validate configuration"""
    if AI_PROVIDER == "gemini":
        if not GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY is required when using Gemini. "
                "Set it in environment variable or .env file"
            )
    elif AI_PROVIDER == "ollama":
        # Ollama doesn't require API key
        pass
    else:
        raise ValueError(f"Invalid AI_PROVIDER: {AI_PROVIDER}. Must be 'ollama' or 'gemini'")
    
    return True

