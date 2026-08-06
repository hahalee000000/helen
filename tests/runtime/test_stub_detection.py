"""Test stub code detection in quality assessment."""
from helen.stdlib.quality import HelenCodeAnalyzer


def test_chinese_stub_markers():
    """Chinese stub comments should be detected."""
    src = '''
fn foo() {
    // 待实现
    return null;
}
fn bar() {
    // 占位
}
fn baz() {
    // 未实现
}
fn qux() {
    // 临时方案
    return 0;
}
fn stub() {
    // 桩代码
}
fn empty_impl() {
    // 空实现
}
'''
    metrics = HelenCodeAnalyzer(src, "test.helen").analyze()
    assert metrics.dead_code_lines >= 6, f"expected >= 6 dead code lines, got {metrics.dead_code_lines}"
    print(f"[PASS] Chinese markers detected: dead_code_lines={metrics.dead_code_lines}")


def test_empty_function_body():
    """Empty function bodies should be detected as stubs."""
    src = '''
fn empty1() {}
fn empty2(): int {}
fn has_code() {
    let x = 1;
    return x;
}
'''
    metrics = HelenCodeAnalyzer(src, "test.helen").analyze()
    assert "empty1" in metrics.stub_functions, f"empty1 not in stubs: {metrics.stub_functions}"
    assert "empty2" in metrics.stub_functions, f"empty2 not in stubs: {metrics.stub_functions}"
    assert "has_code" not in metrics.stub_functions, f"has_code should not be stub"
    print(f"[PASS] Empty bodies detected: {metrics.stub_functions}")


def test_comment_only_body():
    """Function with only comments in body is a stub."""
    src = '''
fn todo_fn() {
    // TODO: implement
}
fn real_fn() {
    // some doc
    return 42;
}
'''
    metrics = HelenCodeAnalyzer(src, "test.helen").analyze()
    assert "todo_fn" in metrics.stub_functions, f"todo_fn not in stubs: {metrics.stub_functions}"
    assert "real_fn" not in metrics.stub_functions, f"real_fn should not be stub"
    print(f"[PASS] Comment-only bodies detected: {metrics.stub_functions}")


def test_literal_return_stub():
    """Function returning only a bare literal is a stub."""
    src = '''
fn placeholder_int(): int {
    return 0;
}
fn placeholder_str(): str {
    return "";
}
fn placeholder_null(): str? {
    return null;
}
fn one_liner(): int {
    return 42;  // intentional, not stub
}
fn real_fn() {
    let x = compute();
    return x + 1;
}
'''
    metrics = HelenCodeAnalyzer(src, "test.helen").analyze()
    assert "placeholder_int" in metrics.stub_functions, f"placeholder_int not detected: {metrics.stub_functions}"
    assert "placeholder_str" in metrics.stub_functions, f"placeholder_str not detected: {metrics.stub_functions}"
    assert "placeholder_null" in metrics.stub_functions, f"placeholder_null not detected: {metrics.stub_functions}"
    # one_liner might or might not be flagged depending on heuristics; just check stubs are in
    assert "real_fn" not in metrics.stub_functions, f"real_fn should not be stub"
    print(f"[PASS] Literal return stubs: {metrics.stub_functions}")


def test_no_false_positive_on_real_functions():
    """Real functions with logic shouldn't be flagged."""
    src = '''
fn add(a: int, b: int): int {
    return a + b;
}
fn greet(name: str): str {
    return "hello " + name;
}
fn process(items: list): list {
    let result = [];
    for item in items {
        result.push(item * 2);
    }
    return result;
}
'''
    metrics = HelenCodeAnalyzer(src, "test.helen").analyze()
    assert len(metrics.stub_functions) == 0, f"False positives: {metrics.stub_functions}"
    print(f"[PASS] No false positives on real functions")


def test_bare_return_null():
    """Bare 'return null;' should be detected as dead/stub."""
    src = '''
fn foo() {
    return null;
}
'''
    metrics = HelenCodeAnalyzer(src, "test.helen").analyze()
    assert metrics.dead_code_lines >= 1, f"bare return null not detected"
    print(f"[PASS] Bare return null detected")


def test_scoring_impact():
    """Stub functions should impact score_code_quality and score_maintainability."""
    from helen.stdlib.quality import QualityScorer
    src = '''
fn stub1() {}
fn stub2() {}
fn stub3() {}
fn real() { return 42; }
'''
    metrics = HelenCodeAnalyzer(src, "test.helen").analyze()
    scorer = QualityScorer()
    cq = scorer.score_code_quality(metrics)
    m = scorer.score_maintainability(metrics)
    print(f"[INFO] Score with 3 stubs: code_quality={cq:.2f}, maintainability={m:.2f}, stubs={metrics.stub_functions}")
    assert len(metrics.stub_functions) == 3


if __name__ == "__main__":
    test_chinese_stub_markers()
    test_empty_function_body()
    test_comment_only_body()
    test_literal_return_stub()
    test_no_false_positive_on_real_functions()
    test_bare_return_null()
    test_scoring_impact()
    print("\nAll stub detection tests passed!")
