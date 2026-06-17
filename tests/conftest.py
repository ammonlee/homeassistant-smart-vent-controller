"""Shared test fixtures.

Uses the official Home Assistant custom-component test harness instead of
hand-rolled module stubs, so tests run against real HA APIs.
"""
import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow Home Assistant to load this custom integration during tests."""
    yield
