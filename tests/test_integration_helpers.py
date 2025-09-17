"""Helper functions for integration tests."""

from unittest.mock import Mock


def create_mock_config_manager(test_config):
    """Create a properly mocked config manager for tests."""
    mock_config_manager = Mock()
    mock_config_manager.config = test_config
    mock_config_manager.get_log_config_dict.return_value = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {'standard': {'format': '%(message)s'}},
        'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'standard'}},
        'loggers': {'': {'level': 'INFO', 'handlers': ['console']}}
    }
    return mock_config_manager