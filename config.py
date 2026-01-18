"""
Configuration for One NZ Employee Finder Agent
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent

# Database configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "employee_directory.db"))

# API configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_RELOAD = os.getenv("API_RELOAD", "True").lower() == "true"

# CORS configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# Privacy & RAI settings
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "60"))
ENABLE_QUERY_LOGGING = os.getenv("ENABLE_QUERY_LOGGING", "True").lower() == "true"
ANONYMIZE_LOGS = os.getenv("ANONYMIZE_LOGS", "True").lower() == "true"

# Agent configuration
MAX_RECOMMENDATIONS = int(os.getenv("MAX_RECOMMENDATIONS", "10"))
MIN_CONFIDENCE_SCORE = float(os.getenv("MIN_CONFIDENCE_SCORE", "0.3"))

# Time saving estimate (from survey)
AVERAGE_TIME_SAVED_MINUTES = float(os.getenv("AVERAGE_TIME_SAVED_MINUTES", "39.3"))

# AI & LLM configuration
USE_AI_ROUTING = os.getenv("USE_AI_ROUTING", "True").lower() == "true"
ENABLE_LLM = os.getenv("ENABLE_LLM", "False").lower() == "true"  # Disabled by default

# LLM Provider settings
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # "openai" or "local"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

# Local LLM settings (for Ollama, LocalAI, etc.)
LOCAL_LLM_ENDPOINT = os.getenv("LOCAL_LLM_ENDPOINT", "http://localhost:11434/v1")
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "llama2")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

