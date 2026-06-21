#!/bin/bash
# Run Helen tests in batches to avoid OOM on memory-constrained systems
# Usage: ./scripts/run_tests_batch.sh

set -e

echo "🧪 Running Helen tests in batches (memory-safe)"
echo "================================================"

# Define test batches (grouped by module dependencies)
batches=(
    "tests/core"
    "tests/lexer"
    "tests/parser"
    "tests/semantic"
    "tests/interpreter"
    "tests/stdlib"
    "tests/ffi"
    "tests/runtime"
    "tests/cli"
    "tests/execution"
    "tests/language"
    "tests/lsp"
    "tests/extension"
    "tests/integration"
    "tests/tutorial"
)

total_passed=0
total_failed=0
failed_batches=()

for batch in "${batches[@]}"; do
    if [ -d "$batch" ]; then
        echo ""
        echo "▶ Running $batch..."
        
        # Run pytest and capture output
        if python -m pytest "$batch" -q --tb=line 2>&1 | tee /tmp/test_batch.log; then
            # Extract test count from last line
            passed=$(grep -oP '\d+ passed' /tmp/test_batch.log | grep -oP '\d+' || echo "0")
            total_passed=$((total_passed + passed))
            echo "  ✅ $passed tests passed"
        else
            # Extract failure info
            failed=$(grep -oP '\d+ failed' /tmp/test_batch.log | grep -oP '\d+' || echo "0")
            passed=$(grep -oP '\d+ passed' /tmp/test_batch.log | grep -oP '\d+' || echo "0")
            total_passed=$((total_passed + passed))
            total_failed=$((total_failed + failed))
            failed_batches+=("$batch")
            echo "  ❌ $failed failed, $passed passed"
        fi
    fi
done

echo ""
echo "================================================"
echo "📊 Summary:"
echo "  Total passed: $total_passed"
echo "  Total failed: $total_failed"

if [ ${#failed_batches[@]} -gt 0 ]; then
    echo ""
    echo "❌ Failed batches:"
    for batch in "${failed_batches[@]}"; do
        echo "  - $batch"
    done
    exit 1
else
    echo ""
    echo "✅ All tests passed!"
    exit 0
fi
