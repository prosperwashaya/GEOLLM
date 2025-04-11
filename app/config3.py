"""
Application configuration settings
"""
import os
import secrets
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration"""
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT') or secrets.token_hex(32)
    DEBUG = False
    TESTING = False
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or \
        f"sqlite:///{os.path.join(basedir, 'app.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 30,
        'pool_size': 10,
        'max_overflow': 20
    }
    
    # Redis
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    
    # Celery
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or REDIS_URL
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or REDIS_URL
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_TIMEZONE = 'UTC'
    CELERY_TASK_ALWAYS_EAGER = False
    CELERY_TASK_CREATE_MISSING_QUEUES = True
    
    # Cache
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = REDIS_URL
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
    
    # JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # Upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    
    # Mail
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'yes', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@geollm.com')
    
    # Rate limiting
    RATELIMIT_DEFAULT = "200 per day;50 per hour;1 per second"
    RATELIMIT_STORAGE_URL = REDIS_URL
    RATELIMIT_STRATEGY = 'fixed-window'
    
    # Logging
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT', 'false').lower() in ['true', 'yes', '1']
    
    # Sentry
    SENTRY_DSN = os.environ.get('SENTRY_DSN')
    SENTRY_TRACES_SAMPLE_RATE = float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', 0.1))
    
    # API settings
    API_TITLE = 'GeoLLM API'
    API_VERSION = 'v1'
    
    # OpenAI API
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo')
    LLM_CACHE_ENABLED = True
    
    # Geospatial APIs
    GOOGLE_EARTH_ENGINE_API_KEY = os.environ.get('GOOGLE_EARTH_ENGINE_API_KEY')
    MAPBOX_ACCESS_TOKEN = os.environ.get('MAPBOX_ACCESS_TOKEN')
    MAPBOX_STYLE_URL = os.environ.get('MAPBOX_STYLE_URL', 'mapbox://styles/mapbox/streets-v11')
    
    # Mock data settings
    USE_MOCK_GEO_DATA = os.environ.get('USE_MOCK_GEO_DATA', 'false').lower() in ['true', 'yes', '1']


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,
        'max_overflow': 10
    }
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)  # Longer tokens for dev
    CELERY_TASK_ALWAYS_EAGER = True  # Run tasks synchronously
    CACHE_TYPE = 'simple'  # Simple in-memory cache for development
    USE_MOCK_GEO_DATA = True
    MAIL_SUPPRESS_SEND = True  # Don't send actual emails in development


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    CELERY_TASK_ALWAYS_EAGER = True
    CACHE_TYPE = 'simple'
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True
    USE_MOCK_GEO_DATA = True
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    """Production configuration"""
    # Server name
    SERVER_NAME = os.environ.get('SERVER_NAME')
    
    # Security
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    
    # SSL
    SSL_REDIRECT = os.environ.get('SSL_REDIRECT', 'true').lower() in ['true', 'yes', '1']
    
    # Proxy setup
    PREFERRED_URL_SCHEME = 'https'
    PROXY_FIX = True
    
    # Rate limiting (stricter for production)
    RATELIMIT_DEFAULT = "100 per day;20 per hour;1 per 3 second"


class DockerDevConfig(DevelopmentConfig):
    """Docker development configuration"""
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI')
    REDIS_URL = 'redis://redis:6379/0'
    CELERY_BROKER_URL = 'redis://redis:6379/0'
    CELERY_RESULT_BACKEND = 'redis://redis:6379/0'
    CACHE_REDIS_URL = 'redis://redis:6379/0'
    RATELIMIT_STORAGE_URL = 'redis://redis:6379/0'


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'docker': DockerDevConfig,
    'default': DevelopmentConfig
}
