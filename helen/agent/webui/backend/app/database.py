from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.services.directory_manager import get_current_cwd, get_project_db_path
from typing import Dict

# Engine 缓存：按工作目录索引
_engines: Dict[str, any] = {}
_session_makers: Dict[str, any] = {}

Base = declarative_base()


def _migrate_attachments_column(engine):
    """自动迁移：为 messages 表添加 attachments 列（如果不存在）

    SQLite 不支持 ALTER TABLE ADD COLUMN IF NOT EXISTS，
    所以先 inspect 检查列是否存在，再决定是否执行 ALTER TABLE。
    """
    try:
        inspector = inspect(engine)
        columns = [c['name'] for c in inspector.get_columns('messages')]
        if 'attachments' not in columns:
            with engine.connect() as conn:
                conn.execute(text(
                    "ALTER TABLE messages ADD COLUMN attachments TEXT"
                ))
                conn.commit()
    except Exception:
        # 迁移失败不影响启动（可能是全新数据库或其他问题）
        pass


def _get_engine_for_cwd(cwd: str):
    """获取或创建指定工作目录的 engine"""
    if cwd not in _engines:
        db_path = get_project_db_path()
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False}
        )
        # 确保表已创建
        Base.metadata.create_all(bind=engine)
        # 自动迁移：为旧数据库添加 attachments 列
        _migrate_attachments_column(engine)
        _engines[cwd] = engine
        _session_makers[cwd] = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    return _engines[cwd]


def _get_session_maker_for_cwd(cwd: str):
    """获取或创建指定工作目录的 session maker"""
    if cwd not in _session_makers:
        _get_engine_for_cwd(cwd)  # 这会同时创建 session maker
    return _session_makers[cwd]


def init_db():
    """初始化数据库（per-project）

    v6.0 单会话架构：DB 按工作目录隔离（<cwd>/.helen/webui.db）。
    不再创建 legacy 的 <cwd>/helen.db（sqlite:///./helen.db）。

    注：此函数现在只是触发一次 per-cwd engine 创建（含 create_all），
    等价于之前 init_db + get_db 的合并效果。
    """
    cwd = get_current_cwd()
    _get_engine_for_cwd(cwd)


# ── 向后兼容：默认 engine 和 SessionLocal ──
#
# 注意：不再在模块导入时自动创建 legacy helen.db。
# 只有真正用到 engine/SessionLocal 时才会按需创建（惰性求值）。
# 新代码应该用 get_db()，它返回 per-project 的 session。
#
# engine/SessionLocal 保留给 tests/ 使用（tests 显式 import 它们）。
# 测试通常会 override get_db 或自己创建 test engine，所以这里的惰性 engine
# 只在测试真的用到时才创建（且会创建在测试的 cwd 下，通常是 /tmp）。


def _get_legacy_engine():
    """惰性获取 legacy engine（仅在测试显式使用时创建）"""
    global _legacy_engine
    if "_legacy_engine" not in globals() or _legacy_engine is None:
        _legacy_engine = create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False}
        )
    return _legacy_engine


class _LazyEngine:
    """惰性 engine 代理：第一次访问时才创建

    目的：避免 import database 时就在 cwd 创建 legacy helen.db。
    生产代码不会用到 legacy engine（都走 per-cwd），只有部分测试会 import。
    """
    def __getattr__(self, name):
        return getattr(_get_legacy_engine(), name)

    def __repr__(self):
        return repr(_get_legacy_engine())


engine = _LazyEngine()


class _LazySessionLocal:
    """惰性 SessionLocal 代理"""
    def __getattr__(self, name):
        global _legacy_session_maker
        if "_legacy_session_maker" not in globals() or _legacy_session_maker is None:
            _legacy_session_maker = sessionmaker(
                autocommit=False, autoflush=False, bind=_get_legacy_engine()
            )
        return getattr(_legacy_session_maker, name)

    def __call__(self, **kwargs):
        global _legacy_session_maker
        if "_legacy_session_maker" not in globals() or _legacy_session_maker is None:
            _legacy_session_maker = sessionmaker(
                autocommit=False, autoflush=False, bind=_get_legacy_engine()
            )
        return _legacy_session_maker(**kwargs)


SessionLocal = _LazySessionLocal()


def get_db():
    """获取当前工作目录的数据库会话

    每次请求根据当前工作目录获取对应的数据库连接。
    切换目录后，新请求会自动使用新目录的数据库。
    """
    cwd = get_current_cwd()
    session_maker = _get_session_maker_for_cwd(cwd)
    db = session_maker()
    try:
        yield db
    finally:
        db.close()
