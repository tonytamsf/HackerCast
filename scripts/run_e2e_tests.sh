#!/bin/bash

# Enhanced E2E Test Runner Script for HackerCast
# This script provides comprehensive E2E testing with detailed reporting

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
REPORTS_DIR="$PROJECT_ROOT/test_reports_$TIMESTAMP"
VENV_PATH="$PROJECT_ROOT/venv"
PYTHON_CMD="python"

# Test configuration
DEFAULT_TEST_LEVEL="standard"
DEFAULT_TIMEOUT="600"
DEFAULT_PARALLEL_WORKERS="auto"

# Banner
print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    HackerCast E2E Test Suite                ║"
    echo "║                 Comprehensive Test Runner                   ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Usage information
print_usage() {
    echo -e "${YELLOW}Usage: $0 [OPTIONS]${NC}"
    echo ""
    echo "Options:"
    echo "  -l, --level LEVEL       Test level: standard, comprehensive, performance (default: standard)"
    echo "  -t, --timeout SECONDS   Test timeout in seconds (default: 600)"
    echo "  -w, --workers COUNT     Parallel workers: number or 'auto' (default: auto)"
    echo "  -m, --markers MARKERS   Pytest markers to run (e.g., 'not network')"
    echo "  -k, --keyword PATTERN   Run tests matching keyword pattern"
    echo "  -v, --verbose           Verbose output"
    echo "  -n, --network          Include network tests"
    echo "  -s, --skip-setup       Skip environment setup"
    echo "  -c, --coverage         Generate coverage report"
    echo "  -r, --report-only      Generate reports from existing results"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Run standard E2E tests"
    echo "  $0 -l comprehensive -v               # Run comprehensive tests with verbose output"
    echo "  $0 -l performance -t 1200            # Run performance tests with 20min timeout"
    echo "  $0 -m 'not network' -c               # Run tests excluding network, with coverage"
    echo "  $0 -k 'test_cli' -w 1                # Run CLI tests with single worker"
}

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_section() {
    echo ""
    echo -e "${PURPLE}▶ $1${NC}"
    echo "─────────────────────────────────────────────────────────────"
}

# Check prerequisites
check_prerequisites() {
    log_section "Checking Prerequisites"

    # Check if we're in the project root
    if [[ ! -f "$PROJECT_ROOT/main.py" ]]; then
        log_error "Not in HackerCast project root. Please run from project directory."
        exit 1
    fi

    # Check Python version
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_CMD="python3"
    elif command -v python >/dev/null 2>&1; then
        PYTHON_CMD="python"
    else
        log_error "Python not found. Please install Python 3.9 or higher."
        exit 1
    fi

    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    log_info "Python version: $PYTHON_VERSION"

    # Check virtual environment
    if [[ -d "$VENV_PATH" ]]; then
        if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
            VENV_PYTHON="$VENV_PATH/Scripts/python.exe"
        else
            VENV_PYTHON="$VENV_PATH/bin/python"
        fi

        if [[ -f "$VENV_PYTHON" ]]; then
            PYTHON_CMD="$VENV_PYTHON"
            log_info "Using virtual environment: $VENV_PATH"
        else
            log_warning "Virtual environment found but Python executable missing"
        fi
    else
        log_warning "Virtual environment not found. Using system Python."
    fi

    # Check required packages
    if ! $PYTHON_CMD -c "import pytest" >/dev/null 2>&1; then
        log_error "pytest not found. Please install requirements: pip install -r requirements.txt"
        exit 1
    fi

    log_success "Prerequisites check completed"
}

# Setup test environment
setup_environment() {
    if [[ "$SKIP_SETUP" == "true" ]]; then
        log_info "Skipping environment setup"
        return
    fi

    log_section "Setting Up Test Environment"

    # Create reports directory
    mkdir -p "$REPORTS_DIR"
    log_info "Created reports directory: $REPORTS_DIR"

    # Create test output directory
    TEST_OUTPUT_DIR="$PROJECT_ROOT/test_output_$TIMESTAMP"
    mkdir -p "$TEST_OUTPUT_DIR"/{data,audio,logs}
    export HACKERCAST_OUTPUT_DIR="$TEST_OUTPUT_DIR"
    log_info "Created test output directory: $TEST_OUTPUT_DIR"

    # Set environment variables
    export HACKERCAST_ENVIRONMENT="test"
    export PYTEST_CURRENT_TEST="1"

    # Create test config if it doesn't exist
    if [[ ! -f "$PROJECT_ROOT/.env.test" ]]; then
        cat > "$PROJECT_ROOT/.env.test" << EOF
HACKERCAST_ENVIRONMENT=test
HACKERCAST_OUTPUT_DIR=$TEST_OUTPUT_DIR
GOOGLE_APPLICATION_CREDENTIALS=
EOF
        log_info "Created .env.test file"
    fi

    log_success "Environment setup completed"
}

# Build pytest command
build_pytest_command() {
    local cmd=("$PYTHON_CMD" "-m" "pytest")

    # Test paths based on level
    case "$TEST_LEVEL" in
        "standard")
            cmd+=("tests/e2e/test_cli_commands.py" "tests/e2e/test_data_validation.py")
            ;;
        "comprehensive")
            cmd+=("tests/e2e/")
            ;;
        "performance")
            cmd+=("tests/e2e/test_performance.py")
            cmd+=("-m" "performance")
            ;;
        *)
            cmd+=("tests/e2e/")
            ;;
    esac

    # Common options
    cmd+=(
        "-v"
        "--tb=short"
        "--strict-markers"
        "--junit-xml=$REPORTS_DIR/junit_results.xml"
        "--timeout=$TIMEOUT"
    )

    # Coverage options
    if [[ "$COVERAGE" == "true" ]]; then
        cmd+=(
            "--cov=."
            "--cov-report=html:$REPORTS_DIR/htmlcov"
            "--cov-report=xml:$REPORTS_DIR/coverage.xml"
            "--cov-report=term"
        )
    fi

    # Parallel workers
    if [[ "$WORKERS" != "1" ]]; then
        cmd+=("--numprocesses=$WORKERS")
    fi

    # Custom markers
    if [[ -n "$MARKERS" ]]; then
        cmd+=("-m" "$MARKERS")
    fi

    # Keyword filter
    if [[ -n "$KEYWORD" ]]; then
        cmd+=("-k" "$KEYWORD")
    fi

    # Network tests
    if [[ "$NETWORK" != "true" && -z "$MARKERS" ]]; then
        cmd+=("-m" "not network")
    fi

    # Verbose output
    if [[ "$VERBOSE" == "true" ]]; then
        cmd+=("--capture=no" "-s")
    fi

    echo "${cmd[@]}"
}

# Run tests
run_tests() {
    log_section "Running E2E Tests"

    local start_time=$(date +%s)
    local cmd
    cmd=$(build_pytest_command)

    log_info "Test level: $TEST_LEVEL"
    log_info "Timeout: $TIMEOUT seconds"
    log_info "Workers: $WORKERS"
    log_info "Command: $cmd"

    echo ""
    log_info "Starting test execution..."

    # Run the tests
    if eval "$cmd"; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log_success "Tests completed successfully in ${duration}s"
        return 0
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log_error "Tests failed after ${duration}s"
        return 1
    fi
}

# Generate comprehensive reports
generate_reports() {
    log_section "Generating Test Reports"

    # HTML Report
    generate_html_report

    # Performance Report
    if [[ "$TEST_LEVEL" == "performance" || "$TEST_LEVEL" == "comprehensive" ]]; then
        generate_performance_report
    fi

    # Coverage Report
    if [[ "$COVERAGE" == "true" ]]; then
        generate_coverage_summary
    fi

    # Test Summary
    generate_test_summary

    log_success "Reports generated in: $REPORTS_DIR"
}

# Generate HTML report
generate_html_report() {
    local html_file="$REPORTS_DIR/test_report.html"

    cat > "$html_file" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>HackerCast E2E Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .header { background: #f4f4f4; padding: 20px; border-radius: 5px; }
        .section { margin: 20px 0; }
        .success { color: #28a745; }
        .error { color: #dc3545; }
        .warning { color: #ffc107; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .timestamp { color: #666; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="header">
        <h1>HackerCast E2E Test Report</h1>
        <p class="timestamp">Generated: $(date)</p>
        <p><strong>Test Level:</strong> $TEST_LEVEL</p>
        <p><strong>Duration:</strong> Test execution time will be shown in summary</p>
    </div>

    <div class="section">
        <h2>Test Configuration</h2>
        <table>
            <tr><th>Parameter</th><th>Value</th></tr>
            <tr><td>Test Level</td><td>$TEST_LEVEL</td></tr>
            <tr><td>Timeout</td><td>$TIMEOUT seconds</td></tr>
            <tr><td>Workers</td><td>$WORKERS</td></tr>
            <tr><td>Network Tests</td><td>$([ "$NETWORK" == "true" ] && echo "Included" || echo "Excluded")</td></tr>
            <tr><td>Coverage</td><td>$([ "$COVERAGE" == "true" ] && echo "Enabled" || echo "Disabled")</td></tr>
        </table>
    </div>

    <div class="section">
        <h2>Artifacts</h2>
        <ul>
            <li><a href="junit_results.xml">JUnit XML Results</a></li>
EOF

    if [[ "$COVERAGE" == "true" ]]; then
        echo "            <li><a href=\"htmlcov/index.html\">Coverage Report</a></li>" >> "$html_file"
    fi

    cat >> "$html_file" << EOF
            <li><a href="test_summary.txt">Test Summary</a></li>
        </ul>
    </div>

    <div class="section">
        <h2>Quick Links</h2>
        <ul>
            <li><a href="../test_output_$TIMESTAMP">Test Output Directory</a></li>
            <li><a href="../.">Project Root</a></li>
        </ul>
    </div>

    <div class="section">
        <p><em>This report was generated by the HackerCast E2E test runner.</em></p>
    </div>
</body>
</html>
EOF

    log_info "HTML report generated: $html_file"
}

# Generate performance report
generate_performance_report() {
    local perf_file="$REPORTS_DIR/performance_report.md"

    cat > "$perf_file" << EOF
# Performance Test Report

**Generated:** $(date)
**Test Level:** $TEST_LEVEL

## Configuration
- Timeout: $TIMEOUT seconds
- Workers: $WORKERS
- Python: $($PYTHON_CMD --version)

## System Information
- OS: $(uname -a)
- Memory: $(free -h 2>/dev/null | grep Mem || echo "Memory info not available")
- Disk Space: $(df -h . | tail -1)

## Performance Metrics
Performance metrics will be extracted from test results if available.

## Test Output Directory
Test artifacts are stored in: $HACKERCAST_OUTPUT_DIR

## Notes
- Performance tests measure execution time, memory usage, and scalability
- Thresholds are defined in test files and enforced automatically
- Historical performance data should be tracked for regression detection
EOF

    log_info "Performance report generated: $perf_file"
}

# Generate coverage summary
generate_coverage_summary() {
    if [[ -f "$REPORTS_DIR/coverage.xml" ]]; then
        log_info "Coverage XML report available: $REPORTS_DIR/coverage.xml"
    fi

    if [[ -d "$REPORTS_DIR/htmlcov" ]]; then
        log_info "Coverage HTML report available: $REPORTS_DIR/htmlcov/index.html"
    fi
}

# Generate test summary
generate_test_summary() {
    local summary_file="$REPORTS_DIR/test_summary.txt"

    cat > "$summary_file" << EOF
HackerCast E2E Test Summary
===========================

Execution Details:
- Timestamp: $TIMESTAMP
- Test Level: $TEST_LEVEL
- Timeout: $TIMEOUT seconds
- Workers: $WORKERS
- Network Tests: $([ "$NETWORK" == "true" ] && echo "Included" || echo "Excluded")
- Coverage: $([ "$COVERAGE" == "true" ] && echo "Enabled" || echo "Disabled")

Test Configuration:
- Python: $($PYTHON_CMD --version)
- Project Root: $PROJECT_ROOT
- Output Directory: $HACKERCAST_OUTPUT_DIR
- Reports Directory: $REPORTS_DIR

Artifacts Generated:
EOF

    # List all files in reports directory
    if [[ -d "$REPORTS_DIR" ]]; then
        echo "- Reports Directory Contents:" >> "$summary_file"
        find "$REPORTS_DIR" -type f -exec basename {} \; | sort | sed 's/^/  - /' >> "$summary_file"
    fi

    # List test output files
    if [[ -d "$HACKERCAST_OUTPUT_DIR" ]]; then
        echo "" >> "$summary_file"
        echo "- Test Output Contents:" >> "$summary_file"
        find "$HACKERCAST_OUTPUT_DIR" -type f | head -20 | sed 's/^/  - /' >> "$summary_file"

        local file_count=$(find "$HACKERCAST_OUTPUT_DIR" -type f | wc -l)
        if [[ $file_count -gt 20 ]]; then
            echo "  - ... and $((file_count - 20)) more files" >> "$summary_file"
        fi
    fi

    log_info "Test summary generated: $summary_file"
}

# Open reports in browser
open_reports() {
    local html_report="$REPORTS_DIR/test_report.html"

    if [[ -f "$html_report" ]]; then
        log_info "Opening test report in browser..."

        if command -v open >/dev/null 2>&1; then
            # macOS
            open "$html_report"
        elif command -v xdg-open >/dev/null 2>&1; then
            # Linux
            xdg-open "$html_report"
        elif command -v start >/dev/null 2>&1; then
            # Windows
            start "$html_report"
        else
            log_info "Please open manually: file://$html_report"
        fi
    fi
}

# Cleanup function
cleanup() {
    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        log_success "E2E tests completed successfully!"
    else
        log_error "E2E tests failed with exit code $exit_code"
    fi

    # Always generate reports
    if [[ "$REPORT_ONLY" != "true" ]]; then
        generate_reports
    fi

    # Show final summary
    echo ""
    log_section "Test Run Summary"
    echo "Reports Directory: $REPORTS_DIR"
    if [[ -n "$HACKERCAST_OUTPUT_DIR" ]]; then
        echo "Test Output Directory: $HACKERCAST_OUTPUT_DIR"
    fi

    if [[ -f "$REPORTS_DIR/test_report.html" ]]; then
        echo "HTML Report: file://$REPORTS_DIR/test_report.html"
    fi

    # Optional cleanup of test output
    if [[ "$CLEANUP_OUTPUT" == "true" && -d "$HACKERCAST_OUTPUT_DIR" ]]; then
        log_info "Cleaning up test output directory..."
        rm -rf "$HACKERCAST_OUTPUT_DIR"
    fi

    exit $exit_code
}

# Main execution
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -l|--level)
                TEST_LEVEL="$2"
                shift 2
                ;;
            -t|--timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            -w|--workers)
                WORKERS="$2"
                shift 2
                ;;
            -m|--markers)
                MARKERS="$2"
                shift 2
                ;;
            -k|--keyword)
                KEYWORD="$2"
                shift 2
                ;;
            -v|--verbose)
                VERBOSE="true"
                shift
                ;;
            -n|--network)
                NETWORK="true"
                shift
                ;;
            -s|--skip-setup)
                SKIP_SETUP="true"
                shift
                ;;
            -c|--coverage)
                COVERAGE="true"
                shift
                ;;
            -r|--report-only)
                REPORT_ONLY="true"
                shift
                ;;
            -h|--help)
                print_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                print_usage
                exit 1
                ;;
        esac
    done

    # Set defaults
    TEST_LEVEL="${TEST_LEVEL:-$DEFAULT_TEST_LEVEL}"
    TIMEOUT="${TIMEOUT:-$DEFAULT_TIMEOUT}"
    WORKERS="${WORKERS:-$DEFAULT_PARALLEL_WORKERS}"
    VERBOSE="${VERBOSE:-false}"
    NETWORK="${NETWORK:-false}"
    SKIP_SETUP="${SKIP_SETUP:-false}"
    COVERAGE="${COVERAGE:-false}"
    REPORT_ONLY="${REPORT_ONLY:-false}"

    # Set trap for cleanup
    trap cleanup EXIT

    # Print banner
    print_banner

    if [[ "$REPORT_ONLY" == "true" ]]; then
        log_info "Report-only mode: generating reports from existing results"
        generate_reports
        open_reports
        exit 0
    fi

    # Execute test pipeline
    check_prerequisites
    setup_environment

    if run_tests; then
        log_success "All tests passed!"
        open_reports
    else
        log_error "Some tests failed. Check reports for details."
        exit 1
    fi
}

# Run main function with all arguments
main "$@"