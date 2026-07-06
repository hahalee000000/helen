# Code Extraction Pitfalls

When extracting Python structures from code files for code-vs-design comparison, regex extraction produces false positives.

## Pitfall 1: Local Variables as Class Fields

`mapping: dict[str, TokenType]` inside a method matched as a Token field. Fix: bound extraction to class body using `@property` or `def __str__` as boundary.

## Pitfall 2: @dataclass Without Args

`@dataclass\nclass ProgramNode(ASTNode)` — no parentheses. Fix: `@dataclass(?:\([^)]*\))?\nclass`

## Pitfall 3: Non-ASCII Docstring Noise

Chinese text in docstrings matches `\w+` field pattern. `注意: ...` appeared as a field. Fix: filter names with `name.isascii() and re.match(r'^[a-zA-Z_]\w*$', name)`.

## Pitfall 4: Trailing Colon

`...\):\n` fails when docstring follows. Fix: remove trailing colon from pattern.

## Golden Template

```python
def extract_dataclass_fields(code, class_name):
    pattern = r'@dataclass(?:\([^)]*\))?\nclass\s+' + re.escape(class_name) + r'\((\w*)\)'
    m = re.search(pattern, code)
    if not m: return None, {}
    remaining = code[m.end():]
    end_match = re.search(r'\n@dataclass|\nclass\s|\n    def accept', remaining)
    body = remaining[:end_match.start()] if end_match else remaining[:500]
    fields = {}
    for fm in re.finditer(r'^\s{4}(\w+)\s*:\s*([^\n#]+)', body, re.MULTILINE):
        name = fm.group(1)
        if name.isascii() and re.match(r'^[a-zA-Z_]\w*$', name):
            fields[name] = fm.group(2).strip()
    return m.group(1), fields
```
