"""Error handling utilities for Smart Vent Controller."""

import logging
from typing import Any, Callable, TypeVar, Optional
from functools import wraps
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)

T = TypeVar('T')


class SmartVentControllerError(HomeAssistantError):
    """Base exception for Smart Vent Controller errors."""
    pass


class EntityUnavailableError(SmartVentControllerError):
    """Raised when an entity is unavailable."""
    pass


class InvalidConfigurationError(SmartVentControllerError):
    """Raised when configuration is invalid."""
    pass


class ServiceCallError(SmartVentControllerError):
    """Raised when a service call fails."""
    pass


def retry_on_failure(
    max_retries: int = 3,
    delay: float = 1.0,
    exceptions: tuple = (Exception,),
    logger: Optional[logging.Logger] = None
):
    """Decorator to retry function calls on failure.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
        exceptions: Tuple of exceptions to catch and retry
        logger: Logger instance (defaults to module logger)
    """
    if logger is None:
        logger = _LOGGER
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries}): {e}. "
                            f"Retrying in {delay}s..."
                        )
                        import asyncio
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} attempts: {e}"
                        )
            raise last_exception
        return wrapper
    return decorator


def safe_float(value: Any, default: float = 0.0, min_val: Optional[float] = None, max_val: Optional[float] = None) -> float:
    """Safely convert value to float with validation.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        min_val: Minimum allowed value (None = no limit)
        max_val: Maximum allowed value (None = no limit)
    
    Returns:
        Float value or default
    """
    try:
        result = float(value)
        if min_val is not None and result < min_val:
            return default
        if max_val is not None and result > max_val:
            return default
        return result
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0, min_val: Optional[int] = None, max_val: Optional[int] = None) -> int:
    """Safely convert value to int with validation.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        min_val: Minimum allowed value (None = no limit)
        max_val: Maximum allowed value (None = no limit)
    
    Returns:
        Int value or default
    """
    try:
        result = int(value)
        if min_val is not None and result < min_val:
            return default
        if max_val is not None and result > max_val:
            return default
        return result
    except (ValueError, TypeError):
        return default


def validate_entity_state(hass: HomeAssistant, entity_id: str, domain: Optional[str] = None) -> bool:
    """Validate that an entity exists and is available.
    
    Args:
        hass: Home Assistant instance
        entity_id: Entity ID to validate
        domain: Optional domain to check
    
    Returns:
        True if entity is valid and available, False otherwise
    """
    if not entity_id:
        return False
    
    # Check domain
    if domain:
        entity_domain = entity_id.split('.')[0] if '.' in entity_id else None
        if entity_domain != domain:
            return False
    
    # Check if entity exists
    if entity_id not in hass.states.async_entity_ids():
        return False
    
    # Check if entity is available
    state = hass.states.get(entity_id)
    if not state:
        return False
    
    if state.state in ["unknown", "unavailable", "None", "none"]:
        return False
    
    return True


def get_safe_state(hass: HomeAssistant, entity_id: str, default: Any = None) -> Any:
    """Safely get entity state.
    
    Args:
        hass: Home Assistant instance
        entity_id: Entity ID
        default: Default value if entity unavailable
    
    Returns:
        Entity state or default
    """
    if not validate_entity_state(hass, entity_id):
        return default
    
    state = hass.states.get(entity_id)
    return state.state if state else default


def get_safe_attribute(hass: HomeAssistant, entity_id: str, attribute: str, default: Any = None) -> Any:
    """Safely get entity attribute.
    
    Args:
        hass: Home Assistant instance
        entity_id: Entity ID
        attribute: Attribute name
        default: Default value if attribute unavailable
    
    Returns:
        Attribute value or default
    """
    if not validate_entity_state(hass, entity_id):
        return default
    
    state = hass.states.get(entity_id)
    if not state:
        return default
    
    return state.attributes.get(attribute, default)


async def safe_service_call(
    hass: HomeAssistant,
    domain: str,
    service: str,
    service_data: dict[str, Any],
    max_retries: int = 3,
    logger: Optional[logging.Logger] = None
) -> bool:
    """Safely call a Home Assistant service with retry logic.
    
    Args:
        hass: Home Assistant instance
        domain: Service domain
        service: Service name
        service_data: Service data
        max_retries: Maximum retry attempts
        logger: Logger instance
    
    Returns:
        True if successful, False otherwise
    """
    if logger is None:
        logger = _LOGGER
    
    for attempt in range(max_retries):
        try:
            await hass.services.async_call(domain, service, service_data)
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(
                    f"Service call {domain}.{service} failed (attempt {attempt + 1}/{max_retries}): {e}. "
                    f"Retrying..."
                )
                import asyncio
                await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
            else:
                logger.error(
                    f"Service call {domain}.{service} failed after {max_retries} attempts: {e}"
                )
                return False
    
    return False


def validate_temperature(temp: Any, min_temp: float = 40.0, max_temp: float = 100.0) -> bool:
    """Validate temperature value.
    
    Args:
        temp: Temperature value to validate
        min_temp: Minimum valid temperature
        max_temp: Maximum valid temperature
    
    Returns:
        True if temperature is valid, False otherwise
    """
    try:
        temp_float = float(temp)
        return min_temp <= temp_float <= max_temp
    except (ValueError, TypeError):
        return False


def validate_vent_position(position: Any) -> bool:
    """Validate vent position value.
    
    Args:
        position: Position value to validate
    
    Returns:
        True if position is valid (0-100), False otherwise
    """
    try:
        pos_int = int(position)
        return 0 <= pos_int <= 100
    except (ValueError, TypeError):
        return False


class ErrorRecovery:
    """Error recovery and state management."""
    
    def __init__(self, hass: HomeAssistant, entry):
        """Initialize error recovery."""
        self.hass = hass
        self.entry = entry
        self._error_counts = {}
        self._last_errors = {}
        self._max_errors_before_disable = 5
        self._error_window = timedelta(minutes=5)
    
    def record_error(self, component: str, error: Exception):
        """Record an error for a component.
        
        Args:
            component: Component name (e.g., 'vent_control', 'thermostat_control')
            error: Exception that occurred
        """
        now = datetime.now()
        
        # Initialize if needed
        if component not in self._error_counts:
            self._error_counts[component] = 0
            self._last_errors[component] = []
        
        # Add error
        self._last_errors[component].append(now)
        
        # Clean old errors outside window
        cutoff = now - self._error_window
        self._last_errors[component] = [
            err_time for err_time in self._last_errors[component]
            if err_time > cutoff
        ]
        
        # Update count
        self._error_counts[component] = len(self._last_errors[component])
        
        _LOGGER.warning(
            f"Error recorded for {component}: {error}. "
            f"Error count: {self._error_counts[component]}/{self._max_errors_before_disable}"
        )
    
    def should_disable_component(self, component: str) -> bool:
        """Check if component should be disabled due to errors.
        
        Args:
            component: Component name
        
        Returns:
            True if component should be disabled
        """
        error_count = self._error_counts.get(component, 0)
        return error_count >= self._max_errors_before_disable
    
    def reset_errors(self, component: str):
        """Reset error count for a component.
        
        Args:
            component: Component name
        """
        if component in self._error_counts:
            self._error_counts[component] = 0
            self._last_errors[component] = []
            _LOGGER.info(f"Error count reset for {component}")

