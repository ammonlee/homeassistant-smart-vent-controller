"""Caching utilities for Smart Vent Controller."""

from typing import Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import logging

_LOGGER = logging.getLogger(__name__)


class TimedCache:
    """Simple time-based cache with TTL."""
    
    def __init__(self, ttl_seconds: int = 5):
        """Initialize cache with TTL.
        
        Args:
            ttl_seconds: Time to live in seconds
        """
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._ttl = timedelta(seconds=ttl_seconds)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None if expired/not found
        """
        if key not in self._cache:
            return None
        
        value, timestamp = self._cache[key]
        
        if datetime.now() - timestamp > self._ttl:
            del self._cache[key]
            return None
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = (value, datetime.now())
    
    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()
    
    def invalidate(self, key: str) -> None:
        """Invalidate a specific cache key.
        
        Args:
            key: Cache key to invalidate
        """
        if key in self._cache:
            del self._cache[key]


class RoomDataCache:
    """Cache for room data to reduce state reads."""
    
    def __init__(self, ttl_seconds: int = 5):
        """Initialize room data cache.
        
        Args:
            ttl_seconds: Cache TTL in seconds
        """
        self._cache = TimedCache(ttl_seconds)
        self._room_keys: set[str] = set()
    
    def get_room_data(self, room_key: str) -> Optional[dict[str, Any]]:
        """Get cached room data.
        
        Args:
            room_key: Room key
        
        Returns:
            Cached room data or None
        """
        return self._cache.get(f"room_{room_key}")
    
    def set_room_data(self, room_key: str, data: dict[str, Any]) -> None:
        """Cache room data.
        
        Args:
            room_key: Room key
            data: Room data to cache
        """
        self._room_keys.add(room_key)
        self._cache.set(f"room_{room_key}", data)
    
    def invalidate_room(self, room_key: str) -> None:
        """Invalidate cached data for a room.
        
        Args:
            room_key: Room key
        """
        self._cache.invalidate(f"room_{room_key}")
    
    def invalidate_all(self) -> None:
        """Invalidate all cached room data."""
        self._cache.clear()
        self._room_keys.clear()


class EntityStateCache:
    """Cache for entity states to reduce state reads."""
    
    def __init__(self, ttl_seconds: int = 2):
        """Initialize entity state cache.
        
        Args:
            ttl_seconds: Cache TTL in seconds
        """
        self._cache = TimedCache(ttl_seconds)
    
    def get_state(self, entity_id: str) -> Optional[Any]:
        """Get cached entity state.
        
        Args:
            entity_id: Entity ID
        
        Returns:
            Cached state or None
        """
        return self._cache.get(f"state_{entity_id}")
    
    def set_state(self, entity_id: str, state: Any) -> None:
        """Cache entity state.
        
        Args:
            entity_id: Entity ID
            state: State to cache
        """
        self._cache.set(f"state_{entity_id}", state)
    
    def invalidate(self, entity_id: str) -> None:
        """Invalidate cached state for an entity.
        
        Args:
            entity_id: Entity ID
        """
        self._cache.invalidate(f"state_{entity_id}")
    
    def invalidate_all(self) -> None:
        """Invalidate all cached states."""
        self._cache.clear()


class ServiceCallBatcher:
    """Batch service calls to reduce overhead."""
    
    def __init__(self, hass, batch_size: int = 10, batch_delay: float = 0.1):
        """Initialize service call batcher.
        
        Args:
            hass: Home Assistant instance
            batch_size: Maximum calls per batch
            batch_delay: Delay between batches in seconds
        """
        self.hass = hass
        self.batch_size = batch_size
        self.batch_delay = batch_delay
        self._pending_calls: list[dict[str, Any]] = []
    
    async def add_call(self, domain: str, service: str, service_data: dict[str, Any]) -> None:
        """Add a service call to the batch.
        
        Args:
            domain: Service domain
            service: Service name
            service_data: Service data
        """
        self._pending_calls.append({
            "domain": domain,
            "service": service,
            "service_data": service_data,
        })
        
        if len(self._pending_calls) >= self.batch_size:
            await self.flush()
    
    async def flush(self) -> None:
        """Execute all pending service calls."""
        if not self._pending_calls:
            return
        
        # Group by domain/service for efficiency
        grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for call in self._pending_calls:
            key = (call["domain"], call["service"])
            grouped[key].append(call["service_data"])
        
        # Execute grouped calls
        for (domain, service), service_data_list in grouped.items():
            if len(service_data_list) == 1:
                # Single call
                await self.hass.services.async_call(
                    domain, service, service_data_list[0]
                )
            else:
                # Multiple calls - execute sequentially but grouped
                for service_data in service_data_list:
                    await self.hass.services.async_call(
                        domain, service, service_data
                    )
                    # Small delay to prevent overwhelming
                    import asyncio
                    await asyncio.sleep(0.01)
        
        self._pending_calls.clear()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - flush remaining calls."""
        await self.flush()

