# 内存系统

> 模块 M7 | `helen/runtime/memory.py` | 测试: `tests/runtime/test_memory.py`

---

## MemoryProvider ABC

```python
class MemoryProvider(ABC):
    @abstractmethod
    def get(self, key: str) -> str | None: ...
    @abstractmethod
    def set(self, key: str, value: str) -> None: ...
    @abstractmethod
    def delete(self, key: str) -> None: ...
    @abstractmethod
    def list_keys(self) -> list[str]: ...
```

---

## FileMemoryProvider

JSON 文件持久化存储：

```python
class FileMemoryProvider(MemoryProvider):
    def __init__(self, path: str):
        self._path = path
        self._data: dict[str, str] = self._load()

    def _load(self) -> dict:
        if os.path.exists(self._path):
            with open(self._path) as f:
                return json.load(f)
        return {}

    def _save(self):
        with open(self._path, 'w') as f:
            json.dump(self._data, f, indent=2)

    def get(self, key: str) -> str | None:
        return self._data.get(key)

    def set(self, key: str, value: str) -> None:
        self._data[key] = value
        self._save()

    def delete(self, key: str) -> None:
        if key in self._data:
            del self._data[key]
            self._save()

    def list_keys(self) -> list[str]:
        return list(self._data.keys())
```

---

## InMemoryProvider

纯内存实现，用于测试：

```python
class InMemoryProvider(MemoryProvider):
    def __init__(self):
        self._data: dict[str, str] = {}

    def get(self, key): return self._data.get(key)
    def set(self, key, value): self._data[key] = value
    def delete(self, key): self._data.pop(key, None)
    def list_keys(self): return list(self._data.keys())
```

---

## 注册与使用

```python
runtime = HelenHermesRuntime()
file_provider = FileMemoryProvider("memories/agent.json")
runtime.register_memory_provider("file", file_provider)

# 通过 Runtime 接口访问
runtime.set_memory("user_name", "Alice")
name = runtime.get_memory("user_name")  # "Alice"
```
