import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ai-api-test-service-dev')
    INTERNAL_TOKEN = os.environ.get('API_TEST_SERVICE_INTERNAL_TOKEN', '')
    REPORT_DIR = os.environ.get('API_TEST_REPORT_DIR', str(BASE_DIR / 'reports'))
    LOG_DIR = os.environ.get('API_TEST_LOG_DIR', str(BASE_DIR / 'logs'))
    SCREENSHOT_DIR = os.environ.get('API_TEST_SCREENSHOT_DIR', str(BASE_DIR / 'reports' / 'screenshots'))
    HTTP_TIMEOUT = float(os.environ.get('API_TEST_HTTP_TIMEOUT', '30'))
