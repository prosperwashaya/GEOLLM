"""
OpenAI API client for LLM operations
"""
import os
import json
import time
import logging
import hashlib
from functools import wraps
from typing import Dict, List, Optional, Union, Any

import openai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from flask import current_app
from app.extensions import cache


# Configure module logger
logger = logging.getLogger(__name__)


def cache_llm_response(f):
    """Decorator to cache LLM responses based on input parameters"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Only cache if caching is enabled
        if not current_app.config.get('LLM_CACHE_ENABLED', False):
            return f(*args, **kwargs)
            
        # Create a cache key from the arguments
        # Sort kwargs keys for consistent hashing
        key_parts = [str(arg) for arg in args]
        for k in sorted(kwargs.keys()):
            key_parts.append(f"{k}={kwargs[k]}")
            
        # Compute MD5 hash to use as the cache key
        cache_key = f"llm_response:{hashlib.md5(':'.join(key_parts).encode()).hexdigest()}"
        
        # Try to get result from cache
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.debug(f"Cache hit for LLM request: {cache_key}")
            return cached_result
            
        # Call the original function
        result = f(*args, **kwargs)
        
        # Store in cache
        cache.set(cache_key, result)
        
        return result
    
    return decorated_function


class OpenAIClient:
    """Client for interacting with OpenAI API"""
    
    def __init__(self, api_key=None, model=None):
        """
        Initialize the OpenAI client
        
        Args:
            api_key: OpenAI API key
            model: Default model to use
        """
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY') or current_app.config.get('OPENAI_API_KEY')
        self.model = model or current_app.config.get('OPENAI_MODEL', 'gpt-3.5-turbo')
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
            
        openai.api_key = self.api_key
        
   
    # Replace it with:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((openai.APITimeoutError, openai.APIError, openai.APIConnectionError))
    )
    @cache_llm_response
    def get_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        stop: Optional[Union[str, List[str]]] = None,
        user: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a completion from the OpenAI Chat API
        
        Args:
            messages: List of message dictionaries with role and content
            model: Model to use for completion
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            frequency_penalty: Frequency penalty parameter
            presence_penalty: Presence penalty parameter
            stop: Stop sequences
            user: End-user identifier for monitoring
            
        Returns:
            OpenAI API response as dictionary
        """
        # Track timing for performance monitoring
        start_time = time.time()
        
        try:
            response = openai.chat.completions.create(
                model=model or self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                stop=stop,
                user=user
            )
            # Calculate duration in milliseconds
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log request stats
            logger.info(
                f"OpenAI request completed: model={model or self.model}, "
                f"tokens={response['usage']['total_tokens']}, "
                f"duration={duration_ms}ms"
            )
            
            return response
            
        except Exception as e:
            # Log error details
            logger.error(f"OpenAI API error: {str(e)}")
            raise
    
    def get_prompt_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Simplified method to get a response to a single prompt
        
        Args:
            prompt: User prompt text
            system_prompt: Optional system prompt
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Text response from the model
        """
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        # Add user prompt
        messages.append({"role": "user", "content": prompt})
        
        # Get completion
        response = self.get_chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content.strip()
    
    def analyze_geospatial_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze a geospatial query to extract parameters and intent
        
        Args:
            query: User geospatial query
            
        Returns:
            Dictionary with extracted parameters and intent
        """
        system_prompt = """
        You are a geospatial analysis assistant. The user will provide a query about
        geospatial data. Your task is to analyze the query and extract:
        
        1. The geographic location or area of interest
        2. The time period of interest (if specified)
        3. The type of data or analysis requested
        4. Any specific parameters, metrics, or thresholds mentioned
        
        Respond with a JSON object containing these fields and provide appropriate
        value types. Be concise and accurate.
        """
        
        prompt = f"Analyze this geospatial query: {query}"
        
        try:
            response = self.get_prompt_response(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.2  # Lower temperature for more deterministic output
            )
            
            # Parse JSON response
            return json.loads(response)
            
        except json.JSONDecodeError:
            # Fallback if response is not valid JSON
            logger.warning(f"Failed to parse JSON from LLM response: {response}")
            return {
                "location": None,
                "time_period": None,
                "data_type": None,
                "parameters": {}
            }
    
    def generate_analysis_report(
        self,
        geospatial_data: Dict[str, Any],
        user_query: str,
        data_description: Optional[str] = None
    ) -> str:
        """
        Generate an analysis report for geospatial data
        
        Args:
            geospatial_data: GeoJSON data or summary
            user_query: Original user query
            data_description: Optional description of the data
            
        Returns:
            Analysis report text
        """
        # Extract basic information from the data
        feature_count = len(geospatial_data.get('features', []))
        data_type = geospatial_data.get('type', 'Unknown')
        
        # Extract feature properties for the first feature as example
        example_properties = {}
        if feature_count > 0:
            first_feature = geospatial_data.get('features', [])[0]
            example_properties = first_feature.get('properties', {})
            
        # Create a summary of the data for the prompt
        data_summary = {
            "type": data_type,
            "featureCount": feature_count,
            "exampleProperties": example_properties
        }
        
        system_prompt = """
        You are a geospatial analysis expert. Based on the provided geospatial data
        summary and the user's original query, generate a comprehensive analysis report.
        The report should be well-structured, informative, and directly address the
        user's question. Include insights about patterns, relationships, or notable
        characteristics in the data. Use markdown formatting for headings and lists.
        """
        
        prompt = f"""
        User Query: {user_query}
        
        Geospatial Data Summary: {json.dumps(data_summary)}
        
        {data_description or ''}
        
        Please generate a detailed analysis report based on this information.
        """
        
        return self.get_prompt_response(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=1000
        )


# Initialize a default client instance
default_client = None

def get_openai_client():
    """Get or create the default OpenAI client"""
    global default_client
    
    if default_client is None:
        default_client = OpenAIClient()
        
    return default_client
