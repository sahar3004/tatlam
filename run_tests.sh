#!/bin/bash
# TATLAM Test Suite Execution Script

set -e  # Exit on error

echo "========================================="
echo "TATLAM Test Suite"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest not found${NC}"
    echo "Install test dependencies with:"
    echo "  pip install -r requirements-test.txt"
    exit 1
fi

# Function to run tests with description
run_test_suite() {
    local name=$1
    local command=$2

    echo -e "${YELLOW}Running: $name${NC}"
    echo "Command: $command"
    echo ""

    if eval "$command"; then
        echo -e "${GREEN}✓ $name PASSED${NC}"
    else
        echo -e "${RED}✗ $name FAILED${NC}"
        return 1
    fi
    echo ""
}

# Parse command line arguments
MODE=${1:-all}

case $MODE in
    unit)
        echo "Running UNIT tests only (fast)..."
        run_test_suite "Unit Tests" "pytest tests/unit/ -v -m unit"
        ;;

    integration)
        echo "Running INTEGRATION tests only..."
        run_test_suite "Integration Tests" "pytest tests/integration/ -v -m integration"
        ;;

    security)
        echo "Running SECURITY tests only..."
        run_test_suite "Security Tests" "pytest tests/security/ -v"
        ;;

    performance)
        echo "Running PERFORMANCE tests only..."
        run_test_suite "Performance Tests" "pytest tests/performance/ -v"
        ;;

    fast)
        echo "Running FAST tests (unit + integration, no slow tests)..."
        run_test_suite "Fast Tests" "pytest tests/unit/ tests/integration/ -v -m 'not slow'"
        ;;

    slow)
        echo "Running SLOW tests (LLM evaluations)..."
        echo -e "${YELLOW}Warning: This will make real API calls${NC}"
        read -p "Continue? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            run_test_suite "LLM Evaluation Tests" "pytest tests/llm_evals/ -v -m slow"
        else
            echo "Cancelled."
            exit 0
        fi
        ;;

    coverage)
        echo "Running tests with COVERAGE report..."
        run_test_suite "Coverage Analysis" "pytest tests/ -m 'not slow' --cov=tatlam --cov-report=html --cov-report=term"
        echo -e "${GREEN}Coverage report generated: htmlcov/index.html${NC}"
        ;;

    parallel)
        echo "Running tests in PARALLEL..."
        run_test_suite "Parallel Test Execution" "pytest tests/ -m 'not slow' -n auto"
        ;;

    all)
        echo "Running ALL tests (excluding slow tests)..."
        echo ""

        run_test_suite "Unit Tests" "pytest tests/unit/ -v -m unit" || true
        run_test_suite "Integration Tests" "pytest tests/integration/ -v -m integration" || true
        run_test_suite "Security Tests" "pytest tests/security/ -v" || true
        run_test_suite "Performance Tests" "pytest tests/performance/ -v" || true

        echo ""
        echo -e "${GREEN}=========================================${NC}"
        echo -e "${GREEN}Test suite complete!${NC}"
        echo -e "${GREEN}=========================================${NC}"
        ;;

    ci)
        echo "Running CI test suite..."
        echo "This runs all tests except expensive LLM evaluations"
        run_test_suite "CI Test Suite" "pytest tests/ -m 'not slow' -v --tb=short"
        ;;

    help|--help|-h)
        echo "Usage: ./run_tests.sh [MODE]"
        echo ""
        echo "Modes:"
        echo "  all          - Run all tests except slow tests (default)"
        echo "  unit         - Run unit tests only (fast)"
        echo "  integration  - Run integration tests only"
        echo "  security     - Run security tests only"
        echo "  performance  - Run performance tests only"
        echo "  fast         - Run unit + integration tests"
        echo "  slow         - Run LLM evaluation tests (requires API keys)"
        echo "  coverage     - Run tests with coverage report"
        echo "  parallel     - Run tests in parallel (requires pytest-xdist)"
        echo "  ci           - Run CI test suite"
        echo "  help         - Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./run_tests.sh unit"
        echo "  ./run_tests.sh coverage"
        echo "  ./run_tests.sh parallel"
        ;;

    *)
        echo -e "${RED}Unknown mode: $MODE${NC}"
        echo "Run './run_tests.sh help' for usage information"
        exit 1
        ;;
esac

exit 0
