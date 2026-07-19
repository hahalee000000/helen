"""Chinese (zh) locale aliases for Helen stdlib.

Maps Chinese function names to canonical English stdlib names.
All aliases are registered at startup alongside the canonical names,
so Chinese code and English code can be freely mixed regardless of
user locale.

Naming conventions:
- Keep names concise and natural in Chinese
- Follow Helen's existing style (snake_case English → meaningful Chinese)
- Prefer verbs for actions (打印 not 输出)
- Prefer nouns for data (列表 not 数组)
- Group related functions with shared prefixes where helpful
  (e.g. json_parse → json解析, json_stringify → json序列化)
"""

# Alias → Canonical name mapping.
# Each entry: "中文别名": "canonical_english_name"
ALIASES: dict[str, str] = {
    # ── Core (核心) ──────────────────────────────────────────────
    "打印": "print",
    "长度": "len",
    "字符串": "str",
    "整数": "int",
    "浮点": "float",
    "布尔": "bool",
    "列表": "list",
    "字典": "dict",
    "绝对值": "abs",
    "最小值": "min",
    "最大值": "max",
    "范围": "range",
    "类型": "type",
    "类型判断": "isinstance",
    "输入": "input",
    "多行输入": "multiline_input",
    "退出": "exit",

    # ── String (字符串操作) ──────────────────────────────────────
    "重复": "repeat",
    "反转": "reverse",
    "左填充": "pad_left",
    "右填充": "pad_right",
    "居中": "center",
    "计数": "count",
    "查找索引": "index",
    "包含": "contains",
    "开头是": "startswith",
    "结尾是": "endswith",
    "转小写": "lower",
    "转大写": "upper",
    "替换": "replace",
    "分割": "split",
    "连接": "join",
    "去除空白": "strip",
    "去前缀": "trim_prefix",
    "去后缀": "trim_suffix",
    "子串": "substring",
    "插值": "interpolate",
    "格式化浮点": "format_float",

    # ── Regex (正则) ─────────────────────────────────────────────
    "正则匹配": "regex_match",
    "正则搜索": "regex_search",
    "正则测试": "regex_test",
    "正则替换": "regex_replace",
    "正则分割": "regex_split",
    "正则查找全部": "regex_findall",

    # ── Text analysis (文本分析) ─────────────────────────────────
    "分词": "tokenize",
    "词频统计": "word_count",
    "编辑距离": "levenshtein",
    "相似度": "similarity",
    "去标点": "remove_punctuation",
    "规范化空白": "normalize_whitespace",
    "提取链接": "extract_urls",
    "提取邮箱": "extract_emails",

    # ── Encoding (编码) ─────────────────────────────────────────
    "base64编码": "base64_encode",
    "base64解码": "base64_decode",
    "html转义": "html_escape",
    "html反转义": "html_unescape",

    # ── Data formats (数据格式) ──────────────────────────────────
    # JSON
    "json解析": "json_parse",
    "json序列化": "json_stringify",
    "json加载": "json_load",
    "json保存": "json_save",
    # HTML
    "html解析": "html_parse",
    "html文本": "html_text",
    "html链接": "html_links",
    "html选择": "html_select",
    # Markdown
    "md转html": "markdown_to_html",
    "md提取标题": "markdown_extract_headings",
    "md解析": "markdown_parse",
    # CSV
    "csv解析": "csv_parse",
    "csv序列化": "csv_stringify",
    "csv加载": "csv_load",
    "csv保存": "csv_save",
    # TOML
    "toml解析": "toml_parse",
    "toml序列化": "toml_stringify",
    "toml加载": "toml_load",
    "toml保存": "toml_save",
    # YAML
    "yaml解析": "yaml_parse",
    "yaml序列化": "yaml_stringify",
    "yaml加载": "yaml_load",
    "yaml保存": "yaml_save",
    # XML
    "xml解析": "xml_parse",
    "xml序列化": "xml_stringify",
    "xml加载": "xml_load",
    "xml保存": "xml_save",

    # ── Collections (集合) ───────────────────────────────────────
    "映射": "map",
    "过滤": "filter",
    "归约": "reduce",
    "查找": "find",
    "条件查找": "find_if",
    "全部满足": "every",
    "部分满足": "some",
    "排序": "sort",
    "去重": "unique",
    "展平": "flatten",
    "分块": "chunk",
    "压缩": "zip",
    "键": "keys",
    "值": "values",
    "键值对": "entries",
    "合并": "merge",
    "选取": "pick",
    "剔除": "omit",
    # Set operations
    "构造集合": "make_set",
    "集合并": "set_union",
    "集合交": "set_intersection",
    "集合差": "set_difference",
    "集合包含": "set_has",
    # List methods (via append_file etc.)
    "追加文件": "append_file",

    # ── Time (时间) ──────────────────────────────────────────────
    "当前时间戳": "now",
    "当前时间": "time",
    "休眠": "sleep",
    "日期": "date",
    "日期时间": "datetime",
    "日期格式化": "date_format",
    "日期解析": "date_parse",
    "日期相加": "date_add",
    "日期相减": "date_diff",
    "年": "date_year",
    "月": "date_month",
    "日": "date_day",
    "星期": "date_weekday",
    # Stopwatch
    "开始计时": "stopwatch_start",
    "经过时间": "stopwatch_elapsed",
    "计时分段": "stopwatch_lap",

    # ── Math / Stats (数学/统计) ─────────────────────────────────
    "平均值": "mean",
    "中位数": "median",
    "众数": "mode",
    "方差": "variance",
    "标准差": "stddev",
    "相关系数": "correlation",
    "百分位": "percentile",
    "求和": "sum",
    "求积": "product",
    "统计最小": "stats_min",
    "统计最大": "stats_max",
    "向上取整": "ceil",
    "向下取整": "floor",
    "四舍五入": "round",
    "平方根": "sqrt",
    # Trigonometric (三角函数)
    "余弦": "cos",
    "正弦": "sin",
    "正切": "tan",
    "反余弦": "acos",
    "反正弦": "asin",
    "反正切": "atan",
    "反正切二": "atan2",
    # Power and logarithmic (幂和对数)
    "幂": "pow",
    "对数": "log",
    "对数二": "log2",
    "对数十": "log10",
    "指数": "exp",

    # ── File I/O (文件读写) ──────────────────────────────────────
    "读文件": "read_file",
    "写文件": "write_file",
    "文件大小": "file_size",
    "文件修改时间": "file_modified",
    "列出目录": "list_dir",
    "遍历目录": "walk_dir",
    "复制文件": "copy_file",
    "移动文件": "move_file",
    "删除文件": "delete_file",
    "删除目录": "delete_dir",
    "创建目录": "mkdir",
    "递归创建目录": "mkdir_p",
    "临时文件": "temp_file",
    "临时目录": "temp_dir",
    "路径基础名": "path_basename",
    "路径目录名": "path_dirname",
    "路径存在": "path_exists",
    "是否目录": "path_is_dir",
    "是否文件": "path_is_file",
    "路径拼接": "path_join",
    "文件哈希": "hash_file",

    # ── System (系统) ────────────────────────────────────────────
    "环境变量获取": "env_get",
    "环境变量设置": "env_set",
    "环境变量删除": "env_delete",
    "环境变量列表": "env_list",
    "命令行参数": "get_cli_args",
    "解析命令行参数": "parse_cli_args",
    "进程ID": "pid",
    "执行": "exec",
    "异步执行": "exec_async",
    "终止进程": "kill",
    # System info (系统信息)
    "操作系统": "platform",
    "主机名": "hostname",
    "系统版本": "platform_version",
    "Python版本": "python_version",
    "CPU核心数": "cpu_count",
    "内存信息": "memory_info",

    # ── Logging (日志) ───────────────────────────────────────────
    "日志调试": "log_debug",
    "日志信息": "log_info",
    "日志警告": "log_warn",
    "日志错误": "log_error",
    "日志严重": "log_critical",
    "日志设置级别": "log_set_level",
    "日志写入文件": "log_to_file",

    # ── Test (测试) ──────────────────────────────────────────────
    "测试用例": "test_case",
    "跳过测试用例": "test_case_skip",
    "测试套件": "test_suite",
    "结束测试套件": "test_end_suite",
    "设置测试超时": "set_test_timeout",
    "运行测试": "run_tests",
    "运行测试json": "run_tests_json",
    "测试计数": "test_count",
    "重置测试": "test_reset",
    "前置所有": "before_all",
    "后置所有": "after_all",
    "前置每个": "before_each",
    "后置每个": "after_each",
    "断言相等": "assert_equal",
    "断言不等": "assert_not_equal",
    "断言为真": "assert_true",
    "断言包含": "assert_contains",
    "断言抛出": "assert_throws",
    "描述": "describe",
    "期望": "expect",
    "它": "it",
    "跳过它": "it_skip",
    "失败": "fail",

    # ── Crypto (加密) ────────────────────────────────────────────
    "md5": "md5",
    "sha1": "sha1",
    "sha256": "sha256",
    "sha512": "sha512",
    "hmac_sha256": "hmac_sha256",

    # ── Random (随机) ────────────────────────────────────────────
    "随机": "random",
    "随机整数": "randint",
    "随机选择": "choice",
    "随机抽样": "sample",
    "洗牌": "shuffle",
    # UUID
    "生成UUID": "uuid_generate",
    "解析UUID": "uuid_from_string",
    "空UUID": "uuid_nil",
    # Random bytes
    "随机字节": "random_bytes",
    "随机十六进制": "random_hex",
    "随机Base64": "random_base64",

    # ── Quality (代码质量) ───────────────────────────────────────
    "分析代码": "analyze_code",
    "安全检查": "check_security",
    "质量评分": "quality_score",
    "质量报告": "quality_report",

    # ── Network (网络) ───────────────────────────────────────────
    "http获取": "http_get",
    "http发布": "http_post",
    "http提交": "http_put",
    "http删除": "http_delete",
    "http下载": "http_download",
    "网页搜索": "web_search",
    "网页获取": "web_fetch",
    "链接解析": "url_parse",
    "链接构建": "url_build",
    "链接编码": "url_encode",
    "链接解码": "url_decode",

    # ── Stream (流式输出) ────────────────────────────────────────
    "流式打印": "stream_print",
    "流式清除": "stream_clear",
    "光标上移": "stream_cursor_up",
    "光标下移": "stream_cursor_down",
    "进度条": "progress_bar",

    # ── Debug / Trace (调试/跟踪) ────────────────────────────────
    "调试": "debug",
    "开启跟踪": "trace_on",
    "关闭跟踪": "trace_off",
    "获取跟踪": "get_trace",

    # ── Tools (工具) ─────────────────────────────────────────────
    "执行命令": "shell_exec",
    "计算表达式": "calculate",
    "修补文件": "patch_file",
    "加载技能": "load_skill",
    "列出技能引用": "list_skill_references",

    # ── Context (上下文管理) ──────────────────────────────────────
    "清除上下文": "clear_context",
    "压缩上下文": "compress_context",
    "定向压缩": "compress_context_target",
    "上下文统计": "context_stats",
    "上下文占用率": "context_usage",
    "获取消息": "get_message",
    "删除消息": "delete_message",
    "钉住消息": "pin_message",
    "取消钉住": "unpin_message",
    "插入消息": "insert_message",
    "替换消息": "replace_message",
    "获取工作记忆": "working_memory_get",
    "设置工作记忆": "working_memory_set",
    "移除工作记忆": "working_memory_remove",
    "清空工作记忆": "working_memory_clear",
    "设置压缩策略": "set_compression_strategy",
    "设置上下文窗口": "set_context_window",
    "设置工作记忆开关": "set_working_memory_enabled",
    "设置缓存感知": "set_cache_aware",
    "获取上下文配置": "get_context_config",
    "搜索上下文": "search_context",
    "上下文切片": "context_slice",
    "导出上下文": "export_context",
    "导入上下文": "import_context",
    "分叉上下文": "fork_context",
    "恢复上下文": "restore_context",
    "压缩回调": "on_compression",
    "溢出回调": "on_context_overflow",

    # ── Transcript (会话记录) ──────────────────────────────────────
    "获取会话id": "get_session_id",
    "列出会话": "list_sessions",
    "回放会话": "replay_transcript",
    "导出会话": "export_transcript",
    "搜索会话": "search_transcript",
    "列出调用": "list_invocations",
    "获取调用": "get_invocation",
    "获取调用树": "get_invocation_tree",
    "调用路径": "invocation_path",
    "压缩审计": "get_compression_audit",
    "恢复会话": "resume_session",
    "获取会话目录": "get_session_dir",
    "设置会话目录": "set_session_dir",
    "删除会话": "delete_session",
    "删除当前会话": "delete_current_session",
    "清理会话": "cleanup_sessions",

    # ── Media/Multimodal (媒体/多模态) ────────────────────────────
    "媒体": "media",
    "媒体base64": "media_base64",
    "是媒体": "is_media",
    "媒体类型": "media_type",

    # ── Media format adapters & utilities (格式适配/工具) ──────
    "转OpenAI格式": "to_openai_parts",
    "转Claude格式": "to_claude_parts",
    "转Gemini格式": "to_gemini_parts",
    "媒体转base64": "media_to_base64",
    "保存媒体": "save_media",
    "是图片": "is_image",
    "是视频": "is_video",
    "是音频": "is_audio",

    # ── File Search (文件搜索) ────────────────────────────────────
    "查找文件": "glob_files",
    "搜索内容": "grep_files",

    # ── Concurrency (并发) ────────────────────────────────────
    "邮箱选择": "mailbox_select",

    # ── LLM Call Control (大模型调用控制) ────────────────────────────────────
    "取消大模型调用": "cancel_llm_call",
    "当前大模型调用id": "current_llm_call_id",
    "取消所有大模型调用": "cancel_all_llm_calls",
}
