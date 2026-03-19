"""Supabase client and FastAPI dependency."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from supabase import Client, create_client

from src.config import settings


@lru_cache
def _create_supabase_client() -> Client:
    """Create Supabase client using the service role key (required for auth.admin.* APIs)."""
    key = settings.supabase_service_role_key or settings.supabase_key
    return create_client(settings.supabase_url, key)


def get_supabase() -> Client:
    """FastAPI dependency that returns the Supabase client."""
    return _create_supabase_client()


# Type alias for dependency injection
SupabaseDep = Annotated[Client, Depends(get_supabase)]
