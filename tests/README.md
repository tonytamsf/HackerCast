# HackerCast Test Suite

This directory contains the comprehensive test suite for the HackerCast application, including unit tests, integration tests, and end-to-end tests.

## Test Structure

```
tests/
├── README.md                    # This file
├── conftest.py                  # Shared test configuration
├── __init__.py                  # Test package init
├── test_*.py                    # Unit tests
├── test_integration.py          # Integration tests
├── e2e/                         # End-to-end tests
│   ├── __init__.py
│   ├── test_cli_commands.py     # CLI command E2E tests
│   ├── test_full_pipeline.py    # Complete pipeline E2E tests
│   ├── test_data_validation.py  # Data quality and validation tests
│   └── test_performance.py      # Performance and benchmark tests
├── fixtures/                    # Test data and fixtures
│   ├── mock_responses.py        # Mock API responses
│   └── test_data.json          # Static test data
└── utils/                       # Test utilities
    ├── test_helpers.py          # Test helper functions
    └── mock_services.py         # Mock external services
```

## Test Categories

### Unit Tests
- **Location**: `tests/test_*.py`
- **Purpose**: Test individual functions and classes in isolation
- **Markers**: `@pytest.mark.unit`
- **Dependencies**: Mocked external services
- **Execution time**: Fast (< 5 seconds per test)

### Integration Tests
- **Location**: `tests/test_integration.py`
- **Purpose**: Test component interactions and data flow
- **Markers**: `@pytest.mark.integration`
- **Dependencies**: Real internal components, mocked external APIs
- **Execution time**: Medium (5-30 seconds per test)

### End-to-End Tests
- **Location**: `tests/e2e/`
- **Purpose**: Test complete user workflows and system behavior
- **Markers**: `@pytest.mark.e2e`
- **Dependencies**: Full application stack with mocked external services
- **Execution time**: Slow (30-300 seconds per test)

### Performance Tests
- **Location**: `tests/e2e/test_performance.py`
- **Purpose**: Validate performance characteristics and scalability
- **Markers**: `@pytest.mark.performance`
- **Dependencies**: Full application with resource monitoring
- **Execution time**: Variable (60-600 seconds per test)

## Running Tests

### Prerequisites
1. Install dependencies: `pip install -r requirements.txt`
2. Ensure virtual environment is activated
3. Set environment variables (see `.env.example`)

### Quick Start
```bash
# Run all unit tests
pytest tests/ -m "unit"

# Run integration tests
pytest tests/ -m "integration"

# Run E2E tests (excluding network)
pytest tests/e2e/ -m "not network"

# Run comprehensive E2E suite
./scripts/run_e2e_tests.sh -l comprehensive
```

### Using the E2E Test Runner Script
The project includes a comprehensive test runner script for E2E tests:

```bash
# Standard E2E tests
./scripts/run_e2e_tests.sh

# Comprehensive E2E tests with coverage
./scripts/run_e2e_tests.sh -l comprehensive -c

# Performance tests only
./scripts/run_e2e_tests.sh -l performance -t 1200

# Network tests included
./scripts/run_e2e_tests.sh -n

# Verbose output with single worker
./scripts/run_e2e_tests.sh -v -w 1

# Help and options
./scripts/run_e2e_tests.sh -h
```

### Test Markers
Use pytest markers to run specific test categories:

```bash
# Unit tests only
pytest -m "unit"

# Integration tests only
pytest -m "integration"

# E2E tests only
pytest -m "e2e"

# Performance tests only
pytest -m "performance"

# Exclude network tests
pytest -m "not network"

# Slow tests only
pytest -m "slow"

# Comprehensive test suite
pytest -m "comprehensive"
```

### Advanced Test Execution
```bash
# Parallel execution with coverage
pytest tests/ --numprocesses=auto --cov=. --cov-report=html

# Specific test file with verbose output
pytest tests/e2e/test_cli_commands.py -v -s

# Run tests matching pattern
pytest -k "test_fetch" -v

# Run with timeout (useful for CI)
pytest tests/ --timeout=300

# Generate JUnit XML for CI
pytest tests/ --junit-xml=test-results.xml
```

## Test Configuration

### Environment Variables
Tests use the following environment variables:
- `HACKERCAST_ENVIRONMENT=test` - Set test environment
- `HACKERCAST_OUTPUT_DIR` - Test output directory
- `PYTEST_CURRENT_TEST=1` - Indicates test execution

### Mock Services
Tests use comprehensive mocking for external dependencies:
- **HackerNews API**: Mocked with realistic test data
- **Web Scraping**: Mocked with predefined content
- **Google TTS**: Mocked audio generation
- **File System**: Isolated test directories

### Test Data
Test data is provided through fixtures:
- `tests/fixtures/test_data.json` - Static test data
- `tests/fixtures/mock_responses.py` - Dynamic mock responses
- `tests/utils/mock_services.py` - Service mocking utilities

## GitHub Actions Integration

The test suite is integrated with GitHub Actions for continuous integration:

### Workflows
1. **Main CI Pipeline** (`.github/workflows/ci.yml`)
   - Runs on push/PR to main branches
   - Multi-OS and Python version matrix
   - Includes linting, unit tests, integration tests
   - Generates coverage reports

2. **E2E Tests** (`.github/workflows/e2e-tests.yml`)
   - Dedicated E2E test execution
   - Multiple test scopes (standard, comprehensive, network)
   - Cross-platform validation

3. **Scheduled Tests** (`.github/workflows/scheduled-tests.yml`)
   - Daily comprehensive tests
   - Health checks every 6 hours
   - Performance benchmarking
   - Network integration tests

### Test Reports
GitHub Actions generates comprehensive test reports:
- JUnit XML results
- Coverage reports (HTML and XML)
- Performance benchmarks
- Test artifacts and logs

## Writing New Tests

### Test Structure Guidelines
1. **Naming**: Use descriptive test names with `test_` prefix
2. **Documentation**: Include docstrings explaining test purpose
3. **Isolation**: Ensure tests are independent and can run in any order
4. **Cleanup**: Use fixtures for setup/teardown
5. **Assertions**: Use clear, specific assertions with helpful messages

### Example Test Structure
```python
import pytest
from tests.utils.test_helpers import TemporaryTestEnvironment
from tests.utils.mock_services import E2ETestContext

class TestNewFeature:
    """Test suite for new feature."""

    def setup_method(self):
        """Setup for each test method."""
        self.test_data = create_test_data()

    @pytest.mark.e2e
    def test_new_feature_basic_functionality(self):
        """Test basic functionality of new feature."""
        with E2ETestContext() as ctx:
            # Test implementation
            result = new_feature_function()

            assert result.success, "Feature should succeed"
            assert result.data is not None, "Feature should return data"

    @pytest.mark.performance
    def test_new_feature_performance(self):
        """Test performance characteristics of new feature."""
        # Performance test implementation
        pass

    def teardown_method(self):
        """Cleanup after each test method."""
        cleanup_test_data()
```

### Mock Service Usage
```python
from tests.utils.mock_services import E2ETestContext

def test_with_mocked_services():
    """Test using mocked external services."""
    with E2ETestContext() as ctx:
        # Configure mock behavior
        ctx.mock_hn_api.set_delay(0.1)
        ctx.mock_scraper.set_failure_mode(False, failure_rate=0.1)

        # Run test
        pipeline = HackerCastPipeline(str(ctx.config_file))
        result = pipeline.run_full_pipeline(limit=3)

        # Assertions
        assert result["success"]
```

## Performance Testing

### Performance Metrics
The test suite tracks key performance metrics:
- **Execution time**: Individual operation and full pipeline timing
- **Memory usage**: Peak memory consumption during operations
- **Scalability**: Performance with different data sizes
- **Concurrency**: Behavior under concurrent execution

### Performance Thresholds
Performance tests enforce the following thresholds:
- Story fetching: < 30 seconds for 20 stories
- Article scraping: < 60 seconds for 10 articles
- Script generation: < 10 seconds
- Full pipeline: < 120 seconds for 5 stories
- Memory usage: < 500MB for typical workloads

### Benchmarking
Run performance benchmarks:
```bash
# Basic performance tests
pytest tests/e2e/test_performance.py -m "performance"

# Comprehensive benchmarks
./scripts/run_e2e_tests.sh -l performance

# Memory profiling
pytest tests/e2e/test_performance.py::test_memory_usage_patterns -v -s
```

## Troubleshooting

### Common Issues

1. **Virtual Environment Not Found**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. **Permission Errors on Test Output**
   ```bash
   # Ensure test output directory is writable
   chmod 755 test_output/
   ```

3. **Network Test Failures**
   ```bash
   # Run without network tests
   pytest tests/ -m "not network"
   ```

4. **Timeout Issues**
   ```bash
   # Increase timeout for slow systems
   pytest tests/ --timeout=600
   ```

5. **Mock Service Issues**
   ```python
   # Reset mock state between tests
   @pytest.fixture(autouse=True)
   def reset_mocks():
       # Reset logic here
       pass
   ```

### Debug Mode
Enable debug mode for detailed test execution:
```bash
# Verbose output with debugging
pytest tests/ -v -s --tb=long --capture=no

# Debug specific test
pytest tests/e2e/test_cli_commands.py::test_fetch_command -v -s --pdb
```

### Log Analysis
Test logs are available in:
- Console output (real-time)
- Test output directory (`test_output_*/logs/`)
- GitHub Actions artifacts (CI runs)

## Contributing

When contributing new tests:
1. Follow the existing test structure and naming conventions
2. Include appropriate test markers
3. Ensure tests are deterministic and fast
4. Add documentation for complex test scenarios
5. Update this README if adding new test categories

### Test Review Checklist
- [ ] Tests are isolated and independent
- [ ] Appropriate markers are used
- [ ] Mock services are properly configured
- [ ] Performance expectations are reasonable
- [ ] Error scenarios are covered
- [ ] Documentation is updated

For questions or issues with the test suite, please open an issue in the project repository.