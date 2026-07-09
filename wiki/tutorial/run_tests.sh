#!/bin/bash
# Tutorial Test Runner
#
# Runs `helen check` on all generated test files and reports results.
#
# Exit codes:
#   0 = all tests passed
#   1 = some tests failed

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTS_DIR="$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TOTAL=0
PASSED=0
FAILED=0
SHOULD_FAIL=0
UNEXPECTED_OK=0
SKIPPED=0

echo "Running tutorial tests..."
echo "Test directory: $TESTS_DIR"
echo

# Find all .helen files
for file in $(find "$TESTS_DIR" -name "*.helen" -type f | sort); do
    TOTAL=$((TOTAL + 1))

    # Get relative path for display
    rel_path="${file#$TESTS_DIR/}"

    # Check if file should fail
    if grep -q "@should_fail" "$file" 2>/dev/null; then
        EXPECTED_FAIL=1
    else
        EXPECTED_FAIL=0
    fi

    # Check if file is skipped
    if grep -q "@skip:" "$file" 2>/dev/null; then
        SKIP_REASON=$(grep "@skip:" "$file" | sed 's/.*@skip: //')
        echo -e "${BLUE}[SKIP]${NC} $rel_path — $SKIP_REASON"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    # Run helen check
    if helen check "$file" > /dev/null 2>&1; then
        # Check passed
        if [ $EXPECTED_FAIL -eq 1 ]; then
            echo -e "${YELLOW}[UNEXPECTED_OK]${NC} $rel_path — should fail but passed"
            UNEXPECTED_OK=$((UNEXPECTED_OK + 1))
        else
            echo -e "${GREEN}[OK]${NC} $rel_path"
            PASSED=$((PASSED + 1))
        fi
    else
        # Check failed
        if [ $EXPECTED_FAIL -eq 1 ]; then
            echo -e "${GREEN}[SHOULD_FAIL]${NC} $rel_path — correctly failed"
            SHOULD_FAIL=$((SHOULD_FAIL + 1))
        else
            echo -e "${RED}[FAIL]${NC} $rel_path"
            FAILED=$((FAILED + 1))
        fi
    fi
done

echo
echo "============================================================"
echo "Summary:"
echo -e "  ${GREEN}Passed: $PASSED${NC}"
echo -e "  ${GREEN}Should fail: $SHOULD_FAIL${NC}"
echo -e "  ${RED}Failed: $FAILED${NC}"
echo -e "  ${YELLOW}Unexpected OK: $UNEXPECTED_OK${NC}"
echo -e "  ${BLUE}Skipped: $SKIPPED${NC}"
echo "  Total: $TOTAL"
echo "============================================================"

# Exit with error if any tests failed
if [ $FAILED -gt 0 ] || [ $UNEXPECTED_OK -gt 0 ]; then
    exit 1
fi

exit 0
