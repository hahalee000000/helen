# 错误码参考

> 45 ErrorCode | `helen/core/errors.py`

---

## 词法错误 (E0300-E0309)

| 代码 | 名称 | 触发条件 |
|---|---|---|
| E0300 | SCANNER_ERROR | 非法字符 |
| E0301 | PARSER_ERROR | 通用语法错误 |
| E0302 | UNEXPECTED_TOKEN | 意外的 Token |
| E0303 | MISSING_TOKEN | 缺少期望的 Token |
| E0304 | INVALID_LITERAL | 无效的数字字面量 |
| E0305 | INVALID_ESCAPE | 无效的转义序列 |
| E0306 | UNTERMINATED_STRING | 字符串未闭合 |
| E0307 | INVALID_IDENTIFIER | 无效标识符 |
| E0308 | DEPRECATED_SYNTAX | 已废弃语法 |
| E0309 | RESERVED_KEYWORD | 使用保留关键字作标识符 |

## 语法错误 (E0310-E0320)

| 代码 | 名称 | 触发条件 |
|---|---|---|
| E0310 | TYPE_MISMATCH | 类型不匹配 |
| E0311 | UNDEFINED_VARIABLE | 未定义变量 |
| E0312 | UNDEFINED_FUNCTION | 未定义函数 |
| E0313 | DUPLICATE_DECLARATION | 重复声明 |
| E0314 | MISSING_RETURN | 缺少返回语句 |
| E0315 | INVALID_BREAK | 无效的 break |
| E0316 | INVALID_CONTINUE | 无效的 continue |
| E0317 | MISSING_DEFAULT_CASE | match 缺少 default |
| E0318 | ASYNC_ON_NON_CALL | async 修饰非 call 语句 |
| E0319 | INVALID_AGENT_PARAM | 无效 Agent 参数 |
| E0320 | UNTERMINATED_BLOCK | 块未闭合 |

## 语义错误 (E0330-E0352)

| 代码 | 名称 | 触发条件 |
|---|---|---|
| E0330 | SEMANTIC_ERROR | 通用语义错误 |
| E0331 | SEMANTIC_TYPE_ERROR | 语义类型错误 |
| E0332 | UNDECLARED_VARIABLE | 未声明变量 |
| E0333 | DUPLICATE_SYMBOL | 重复符号 |
| E0334 | AGENT_RUNTIME_ERROR | Agent 运行时错误 |
| E0335 | DUPLICATE_AGENT_NAME | 重复 Agent 名 |
| E0336 | DUPLICATE_PARAM | 重复参数名 |
| E0337 | MISSING_PROMPT | Agent 缺少 prompt |
| E0338 | BREAK_OUTSIDE_LOOP | break 在循环外 |
| E0339 | CONTINUE_OUTSIDE_LOOP | continue 在循环外 |
| E0340 | RETURN_OUTSIDE_FUNCTION | return 在函数外 |
| E0341 | IMPORT_NOT_FOUND | 导入文件不存在 |
| E0342 | INVALID_CATCH_TYPE | 无效 catch 类型 |
| E0343 | CATCH_ALL_NOT_LAST | catch-all 不在最后 |
| E0344 | LLM_IF_NO_DEFAULT | llm if 缺少 default |
| E0345 | MATCH_NO_DEFAULT | match 缺少 default |
| E0346 | CONST_ASSIGNMENT | 常量赋值 |
| E0347 | AGENT_PARAM_MISMATCH | Agent 参数不匹配 |
| E0348 | INVALID_AGENT_NAME | 无效 Agent 名 |
| E0349 | MISSING_DEFAULT_BRANCH | 缺少默认分支 |
| E0350 | SCOPE_VIOLATION | 跨 Agent 变量引用 (v1.10: 模块级 let 在 agent main 中不可见) |
| E0351 | SHARED_NOT_MODULE_LEVEL | shared let 不在模块级声明 (v1.10) |
| E0352 | IMMUTABLE_ASSIGNMENT | 子脚本/字段赋值目标不可变 (v1.10) |

---

## v1.10 新增错误码详解

### E0350: SCOPE_VIOLATION — 模块级 let 在 agent main 中不可见

**触发条件**: Agent main 试图访问模块级 let 变量

**示例**:
```helen
let moduleVar = "模块级"

agent MyAgent {
  main {
    print(moduleVar)  // ❌ E0350 SCOPE_VIOLATION
  }
}
```

**错误消息**:
```
Error at line 6: Module-level let 'moduleVar' is not visible in agent 'MyAgent' main.
Use 'shared let' to make it accessible.
```

**修正方法**:
```helen
// 方法 1: 使用 shared let
shared let moduleVar = "模块级"

agent MyAgent {
  main {
    print(moduleVar)  // ✅ 可以访问
  }
}

// 方法 2: 使用 const（只读）
const MODULE_CONST = "常量"

agent MyAgent {
  main {
    print(MODULE_CONST)  // ✅ 只读访问
  }
}
```

### E0351: SHARED_NOT_MODULE_LEVEL — shared let 不在模块级声明

**触发条件**: `shared let` 在非模块级作用域中声明

**示例**:
```helen
agent MyAgent {
  shared let agentShared = 0  // ❌ E0351 SHARED_NOT_MODULE_LEVEL
  
  main {
    // ...
  }
}

fn myFunction() {
  shared let fnShared = 0  // ❌ E0351 SHARED_NOT_MODULE_LEVEL
}
```

**错误消息**:
```
Error at line 2: 'shared let' must be declared at module level, not inside agent or function.
```

**修正方法**:
```helen
// shared let 必须在模块级声明
shared let SHARED_VAR = 0

agent MyAgent {
  main {
    SHARED_VAR += 1  // ✅ 可以访问
  }
}
```

### E0352: IMMUTABLE_ASSIGNMENT — 子脚本/字段赋值目标不可变

**触发条件**: 试图修改 const 变量的元素或字段

**示例**:
```helen
const arr = [1, 2, 3]
arr[0] = 10  // ❌ E0352 IMMUTABLE_ASSIGNMENT

const obj = {"name": "Alice"}
obj.name = "Bob"  // ❌ E0352 IMMUTABLE_ASSIGNMENT
```

**错误消息**:
```
Error at line 2: Cannot modify element of const variable 'arr'.
```

**修正方法**:
```helen
// 使用 let 声明可变变量
let arr = [1, 2, 3]
arr[0] = 10  // ✅ 可以修改

let obj = {"name": "Alice"}
obj.name = "Bob"  // ✅ 可以修改
```

---

## 错误码统计

| 类别 | 范围 | 数量 |
|------|------|------|
| 词法错误 | E0300-E0309 | 10 |
| 语法错误 | E0310-E0320 | 11 |
| 语义错误 | E0330-E0352 | 23 |
| **总计** | | **45** |

### v1.10 新增

- E0350: SCOPE_VIOLATION（更新说明）
- E0351: SHARED_NOT_MODULE_LEVEL
- E0352: IMMUTABLE_ASSIGNMENT

---

**最后更新**: 2026-07-01  
**版本**: v1.10
