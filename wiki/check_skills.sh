#!/bin/bash
# 检查 skill 代码块

cd /home/rxx/helen

echo "检查 skill 代码块..."
echo ""

total=0
passed=0
failed=0

# 遍历所有测试文件
while IFS= read -r file; do
    if [ -f "$file" ]; then
        total=$((total + 1))

        # 运行 helen check
        output=$(helen check "$file" 2>&1)
        exit_code=$?

        if [ $exit_code -eq 0 ]; then
            passed=$((passed + 1))
        else
            failed=$((failed + 1))
            # 提取错误信息
            error_msg=$(echo "$output" | grep "错误\|Error" | head -1)
            echo "❌ $file"
            echo "   $error_msg"
            echo ""
        fi
    fi
done < <(find wiki/skill_tests -name "*.helen" -type f)

echo "========================================="
echo "总计: $total"
echo "通过: $passed"
echo "失败: $failed"
echo "========================================="
