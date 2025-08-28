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
                cls._instance = create_client(
                    settings.SUPABASE_URL,
                    settings.SUPABASE_ANON_KEY
                )
                logger.info("Supabase client initialized successfully")
            except TypeError as e:
                logger.error(f"Supabase client TypeError - likely version issue: {e}")
                # Try with minimal arguments in case of version conflicts
                try:
                    cls._instance = create_client(
                        settings.SUPABASE_URL,
                        settings.SUPABASE_ANON_KEY
                    )
                    logger.info("Supabase client initialized with fallback method")
                except Exception as e2:
                    logger.error(f"Fallback initialization also failed: {e2}")
                    raise
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                raise
        return cls._instance
    
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