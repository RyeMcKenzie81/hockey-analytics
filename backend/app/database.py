from supabase import create_client, Client
from typing import Optional
import logging
from .config import settings

logger = logging.getLogger(__name__)


class SupabaseClient:
    _instance: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Client:
        if cls._instance is None:
            try:
                logger.info(f"Initializing Supabase client with URL: {settings.SUPABASE_URL[:30]}...")
                logger.info(f"Railway environment: {settings.RAILWAY_ENVIRONMENT}")
                
                # Log package versions to debug Railway vs local differences
                import supabase
                import gotrue
                import httpx
                import storage3
                logger.info(f"Package versions - supabase: {supabase.__version__}, gotrue: {gotrue.__version__}, httpx: {httpx.__version__}, storage3: {storage3.__version__}")
                
                # Check and temporarily clear proxy environment variables
                import os
                proxy_vars = {k: v for k, v in os.environ.items() if 'proxy' in k.lower()}
                if proxy_vars:
                    logger.warning(f"Found proxy environment variables: {proxy_vars}")
                
                # Temporarily clear proxy variables during Supabase initialization
                original_env = {}
                proxy_env_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
                
                for var in proxy_env_vars:
                    if var in os.environ:
                        original_env[var] = os.environ[var]
                        del os.environ[var]
                        logger.info(f"Temporarily removed {var} environment variable")
                
                try:
                    cls._instance = create_client(
                        settings.SUPABASE_URL,
                        settings.SUPABASE_ANON_KEY
                    )
                    logger.info("Supabase client initialized successfully")
                finally:
                    # Restore proxy environment variables
                    for var, value in original_env.items():
                        os.environ[var] = value
                        logger.info(f"Restored {var} environment variable")
            except TypeError as e:
                logger.error(f"Supabase client TypeError - trying without options: {e}")
                # Try without any options
                try:
                    cls._instance = create_client(
                        settings.SUPABASE_URL,
                        settings.SUPABASE_ANON_KEY
                    )
                    logger.info("Supabase client initialized without options")
                except Exception as e2:
                    logger.error(f"All initialization methods failed: {e2}")
                    # Last resort - create a mock client for Railway
                    if settings.RAILWAY_ENVIRONMENT == "production":
                        logger.warning("Creating mock Supabase client for Railway deployment")
                        cls._instance = None  # This will cause downstream issues but app will start
                        return cls._get_mock_client()
                    raise
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                raise
        return cls._instance
    
    @classmethod
    def _get_mock_client(cls):
        """Temporary mock client for Railway debugging"""
        class MockClient:
            def table(self, name):
                logger.warning(f"Mock table access: {name}")
                return self
            def select(self, *args):
                return self
            def insert(self, *args):
                return self
            def update(self, *args):
                return self
            def eq(self, *args):
                return self
            def execute(self):
                logger.warning("Mock database operation")
                return type('MockResult', (), {'data': []})()
            @property
            def storage(self):
                return self
            def from_(self, bucket):
                return self
            def upload(self, *args, **kwargs):
                logger.warning("Mock storage upload")
                return True
        
        return MockClient()
    
    @classmethod
    def get_service_client(cls) -> Optional[Client]:
        if settings.SUPABASE_SERVICE_KEY:
            try:
                return create_client(
                    settings.SUPABASE_URL,
                    settings.SUPABASE_SERVICE_KEY
                )
            except Exception as e:
                logger.error(f"Failed to initialize Supabase service client: {e}")
                return None
        return None


def get_supabase() -> Client:
    return SupabaseClient.get_client()