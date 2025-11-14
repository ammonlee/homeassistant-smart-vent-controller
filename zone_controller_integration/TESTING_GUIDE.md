# Testing Guide for Smart Vent Controller Integration

## Overview

This guide explains how to run and write tests for the Smart Vent Controller integration.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Pytest fixtures and configuration
├── test_error_handling.py   # Error handling utilities tests
├── test_device.py           # Device registry tests
├── test_config_flow.py      # Config flow tests
└── test_sensors.py          # Sensor platform tests
```

## Prerequisites

### Install Test Dependencies

```bash
cd smart_vent_controller_integration
pip install -r requirements-test.txt
```

### Required Packages

- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `pytest-homeassistant-custom-component` - Home Assistant test utilities
- `pytest-mock` - Mocking utilities

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_error_handling.py
```

### Run Specific Test

```bash
pytest tests/test_error_handling.py::test_safe_float_valid
```

### Run with Verbose Output

```bash
pytest -v
```

### Run with Coverage

```bash
pytest --cov=custom_components.smart_vent_controller --cov-report=html
```

## Test Fixtures

### `mock_hass`

Mock Home Assistant instance with:
- `states` - State machine mock
- `services` - Service registry mock
- `config_entries` - Config entry mock

### `mock_entry`

Mock config entry with:
- Sample thermostat configuration
- Sample room configurations
- Default options

### `mock_coordinator`

Mock coordinator instance linked to mock_hass and mock_entry.

### `mock_thermostat_state`

Mock thermostat state with heating mode and temperature attributes.

### `mock_room_climate_state`

Mock room climate state with temperature attributes.

### `mock_vent_state`

Mock vent state with position attribute.

### `mock_occupancy_state`

Mock occupancy sensor state.

## Writing Tests

### Example: Testing Error Handling

```python
def test_safe_float_valid():
    """Test safe_float with valid values."""
    assert safe_float("72.5") == 72.5
    assert safe_float(72.5) == 72.5
```

### Example: Testing Async Functions

```python
@pytest.mark.asyncio
async def test_async_function(mock_hass, mock_entry):
    """Test async function."""
    result = await async_function(mock_hass, mock_entry)
    assert result is not None
```

### Example: Testing with Mocks

```python
def test_with_mock(mock_hass):
    """Test with mocked Home Assistant."""
    mock_hass.states.get.return_value = mock_state
    result = function_under_test(mock_hass)
    assert result == expected_value
```

## Test Categories

### Unit Tests

Test individual functions and classes in isolation:
- `test_error_handling.py` - Error handling utilities
- `test_device.py` - Device registry helpers

### Integration Tests

Test components working together:
- `test_config_flow.py` - Configuration flow
- `test_sensors.py` - Sensor platform

## Test Coverage Goals

- **Error Handling:** 100% coverage
- **Device Registry:** 100% coverage
- **Config Flow:** >90% coverage
- **Platforms:** >80% coverage
- **Scripts:** >70% coverage
- **Automations:** >70% coverage

## Running Tests in CI/CD

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements-test.txt
      - run: pytest
```

## Best Practices

### 1. Test Naming

- Use descriptive test names: `test_function_name_scenario`
- Example: `test_safe_float_invalid_input_returns_default`

### 2. Test Organization

- Group related tests in the same file
- Use fixtures for common setup
- Keep tests independent

### 3. Mocking

- Mock external dependencies
- Use fixtures for reusable mocks
- Verify mock calls when important

### 4. Assertions

- Use specific assertions
- Include helpful error messages
- Test edge cases

### 5. Async Testing

- Use `@pytest.mark.asyncio` for async tests
- Use `AsyncMock` for async mocks
- Await async calls properly

## Troubleshooting

### Import Errors

If you get import errors:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Async Test Issues

Make sure `pytest-asyncio` is installed and configured:
```python
@pytest.mark.asyncio
async def test_async():
    ...
```

### Mock Issues

Ensure mocks are properly configured:
```python
mock_hass.states.get.return_value = mock_state
```

## Next Steps

1. **Add More Tests:**
   - Script tests (vent control, thermostat control)
   - Automation tests
   - Binary sensor tests
   - Number platform tests
   - Switch platform tests

2. **Integration Tests:**
   - End-to-end tests
   - Service call tests
   - Entity update tests

3. **Performance Tests:**
   - Load testing
   - Response time testing

4. **Coverage Reports:**
   - Generate HTML coverage reports
   - Track coverage over time

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Home Assistant Testing](https://developers.home-assistant.io/docs/development_testing/)
- [pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component)

