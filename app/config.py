# Add to app/config.py in the Config class:
import os


# Add these to your existing Config class in app/config.py

# Add these to your existing Config class in app/config.py

# LLM configuration
DEFAULT_LLM_PROVIDER = os.environ.get('DEFAULT_LLM_PROVIDER', 'openai')

# OpenAI API
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-3.5-turbo')
# Hugging Face API
HUGGINGFACE_API_KEY = os.environ.get("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")
HUGGINGFACE_API_URL = "https://api-inference.huggingface.co/models/"
HUGGINGFACE_DEFAULT_MODEL = "mistralai/Mistral-7B-Instruct-v0.2"

# Groq API
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
GROQ_DEFAULT_MODEL = os.environ.get('GROQ_DEFAULT_MODEL', 'llama3-8b-8192')

# Create a new file: app/llm/huggingface_client.py

"""
Hugging Face API client for alternative LLM operations
"""
import os
import json
import requests
import logging
from functools import wraps
from typing import Dict, List, Optional, Union, Any

from flask import current_app
from app.extensions import cache

import os
import secrets
from datetime import timedelta
from dotenv import load_dotenv


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
     # Geospatial APIs
    GOOGLE_EARTH_ENGINE_API_KEY = os.environ.get('GOOGLE_EARTH_ENGINE_API_KEY')
    GEE_SERVICE_ACCOUNT_KEY = os.environ.get('GEE_SERVICE_ACCOUNT_KEY')
    MAPBOX_ACCESS_TOKEN = os.environ.get('MAPBOX_ACCESS_TOKEN')
    MAPBOX_STYLE_URL = os.environ.get('MAPBOX_STYLE_URL', 'mapbox://styles/mapbox/streets-v11')
    
    # Geospatial data settings - Always use Earth Engine
    USE_MOCK_GEO_DATA = False  # Force to False to always use Earth Engine
    USE_EARTH_ENGINE_AS_DEFAULT = True


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
    USE_MOCK_GEO_DATA = False  # Force to False even in dev
    USE_EARTH_ENGINE_AS_DEFAULT = True  # Use Earth Engine in dev
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
    USE_MOCK_GEO_DATA = False  # Force to False even in testing
    USE_EARTH_ENGINE_AS_DEFAULT = True  # Use Earth Engine in testing
    RATELIMIT_ENABLED = False


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




# Configure module logger
logger = logging.getLogger(__name__)

class HuggingFaceClient:
    """Client for interacting with Hugging Face Inference API"""
    
    def __init__(self, api_key=None, api_url=None, default_model=None):
        """
        Initialize the Hugging Face client
        
        Args:
            api_key: Hugging Face API key
            api_url: Base URL for Hugging Face API
            default_model: Default model to use
        """
        self.api_key = api_key or os.environ.get('HUGGINGFACE_API_KEY') or current_app.config.get('HUGGINGFACE_API_KEY')
        self.api_url = api_url or current_app.config.get('HUGGINGFACE_API_URL', "https://api-inference.huggingface.co/models/")
        self.default_model = default_model or current_app.config.get('HUGGINGFACE_DEFAULT_MODEL', "mistralai/Mistral-7B-Instruct-v0.2")
        
        if not self.api_key:
            logger.warning("Hugging Face API key is not set. API calls will likely fail.")
    
    def query(self, payload: Dict[str, Any], model: Optional[str] = None) -> Dict[str, Any]:
        """
        Query the Hugging Face model
        
        Args:
            payload: Dict containing the query parameters
            model: Model to use (defaults to self.default_model)
        
        Returns:
            API response as dictionary
        """
        model_name = model or self.default_model
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        try:
            response = requests.post(
                f"{self.api_url}{model_name}",
                headers=headers,
                json=payload
            )
            response.raise_for_status()  # Raise exception for 4XX/5XX responses
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Hugging Face API error: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response status: {e.response.status_code}, Content: {e.response.text}")
            raise
    
    def get_text_generation(self, 
                          prompt: str, 
                          model: Optional[str] = None,
                          max_length: int = 500,
                          temperature: float = 0.7,
                          top_p: float = 0.9,
                          top_k: int = 50) -> str:
        """
        Generate text using a Hugging Face model
        
        Args:
            prompt: Text prompt
            model: Model to use
            max_length: Maximum length of generated text
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
        
        Returns:
            Generated text
        """
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_length": max_length,
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k
            }
        }
        
        response = self.query(payload, model)
        
        # Handle different response formats
        if isinstance(response, list) and len(response) > 0:
            if 'generated_text' in response[0]:
                return response[0]['generated_text']
            return response[0]
        
        return str(response)
    
    def get_chat_completion(self, 
                          messages: List[Dict[str, str]], 
                          model: Optional[str] = None,
                          max_tokens: int = 500,
                          temperature: float = 0.7) -> str:
        """
        Generate chat completion using a Hugging Face model
        
        Args:
            messages: List of message dictionaries with role and content
            model: Model to use
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
        
        Returns:
            Generated response text
        """
        # Format messages for the model (format may vary by model)
        formatted_prompt = ""
        
        for message in messages:
            role = message.get('role', '').lower()
            content = message.get('content', '')
            
            if role == 'system':
                formatted_prompt += f"<|system|>\n{content}\n"
            elif role == 'user':
                formatted_prompt += f"<|user|>\n{content}\n"
            elif role == 'assistant':
                formatted_prompt += f"<|assistant|>\n{content}\n"
        
        formatted_prompt += "<|assistant|>\n"
        
        payload = {
            "inputs": formatted_prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "return_full_text": False
            }
        }
        
        response = self.query(payload, model)
        
        # Extract the generated text
        if isinstance(response, list) and len(response) > 0:
            if 'generated_text' in response[0]:
                return response[0]['generated_text']
            return response[0]
        
        return str(response)
    
    def analyze_geospatial_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze a geospatial query using a Hugging Face model
        
        Args:
            query: User geospatial query
        
        Returns:
            Dictionary with extracted parameters
        """
        # Construct a prompt that instructs the model to extract structured information
        system_message = """
        You are a geospatial analysis assistant. The user will provide a query about
        geospatial data. Extract the following information in JSON format:
        - location: The geographic location or area of interest
        - time_period: The time period of interest (if specified)
        - data_type: The type of data or analysis requested
        - parameters: Any specific parameters, metrics, or thresholds mentioned
        
        Return only valid JSON with these fields.
        """
        
        prompt = f"Analyze this geospatial query: {query}"
        
        # Construct the messages
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.get_chat_completion(messages)
            
            # Try to parse the response as JSON
            # First, look for JSON within the text using simple heuristic
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                parsed_response = json.loads(json_str)
                return parsed_response
            else:
                # If we can't find JSON, try to parse the whole response
                return json.loads(response)
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse JSON from LLM response: {response}")
            logger.warning(f"Error: {str(e)}")
            
            # Return a default structure if parsing fails
            return {
                "location": None, 
                "time_period": None,
                "data_type": None,
                "parameters": {}
            }

# Initialize a default client instance
default_client = None

def get_huggingface_client():
    """Get or create the default Hugging Face client"""
    global default_client
    
    if default_client is None:
        default_client = HuggingFaceClient()
        
    return default_client
