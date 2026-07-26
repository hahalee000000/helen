"""目录管理器测试

验证 directory_manager 模块的基本功能。

运行: cd webui/backend && pytest tests/test_directory_manager.py -v
"""
import pytest
import tempfile
from pathlib import Path
from app.services.directory_manager import (
    get_current_cwd,
    set_current_cwd,
    get_display_name,
    get_project_db_path,
    get_project_helen_session_dir,
    get_project_memory_path,
    get_project_user_path,
    cwd_to_session_id,
)


class TestDirectoryManager:
    """目录管理器测试"""

    def test_get_current_cwd(self):
        """获取当前工作目录"""
        cwd = get_current_cwd()
        assert isinstance(cwd, str)
        assert len(cwd) > 0
        assert Path(cwd).is_absolute()

    def test_set_current_cwd_valid(self):
        """切换到有效目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = set_current_cwd(tmpdir)
            assert result["status"] == "ok"
            assert result["cwd"] == tmpdir
            assert result["display_name"] == Path(tmpdir).name

            # 验证全局变量已更新
            assert get_current_cwd() == tmpdir

    def test_set_current_cwd_invalid(self):
        """切换到无效目录"""
        result = set_current_cwd("/nonexistent/path/12345")
        assert result["status"] == "error"
        assert "目录不存在" in result["message"]

    def test_set_current_cwd_creates_helen_dir(self):
        """切换目录时自动创建 .helen 目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = set_current_cwd(tmpdir)
            assert result["status"] == "ok"

            # 验证 .helen 目录已创建
            helen_dir = Path(tmpdir) / ".helen"
            assert helen_dir.exists()
            assert helen_dir.is_dir()

    def test_get_display_name(self):
        """获取目录显示名称"""
        # 普通目录
        name = get_display_name("/home/user/project")
        assert name == "project"

        # 嵌套目录
        name = get_display_name("/tmp/a/b/c")
        assert name == "c"

    def test_get_project_db_path(self):
        """获取项目数据库路径"""
        with tempfile.TemporaryDirectory() as tmpdir:
            set_current_cwd(tmpdir)
            db_path = get_project_db_path()

            # 验证路径正确
            assert db_path.parent == Path(tmpdir) / ".helen"
            assert db_path.name == "webui.db"

            # 验证 .helen 目录已创建
            assert db_path.parent.exists()

    def test_get_project_helen_session_dir(self):
        """获取 Helen session 目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            set_current_cwd(tmpdir)
            session_dir = get_project_helen_session_dir()

            # 验证路径正确
            assert session_dir == Path(tmpdir) / ".helen" / "sessions"

    def test_get_project_memory_path(self):
        """获取 MEMORY.md 路径"""
        with tempfile.TemporaryDirectory() as tmpdir:
            set_current_cwd(tmpdir)
            memory_path = get_project_memory_path()

            # 验证路径正确
            assert memory_path == Path(tmpdir) / ".helen" / "MEMORY.md"

    def test_get_project_user_path(self):
        """获取 USER.md 路径"""
        with tempfile.TemporaryDirectory() as tmpdir:
            set_current_cwd(tmpdir)
            user_path = get_project_user_path()

            # 验证路径正确
            assert user_path == Path(tmpdir) / ".helen" / "USER.md"

    def test_directory_isolation(self):
        """验证不同目录的数据库路径独立"""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                # 切换到目录 1
                set_current_cwd(tmpdir1)
                db_path_1 = get_project_db_path()

                # 切换到目录 2
                set_current_cwd(tmpdir2)
                db_path_2 = get_project_db_path()

                # 验证路径不同
                assert db_path_1 != db_path_2
                assert str(tmpdir1) in str(db_path_1)
                assert str(tmpdir2) in str(db_path_2)

    def test_cwd_to_session_id_deterministic(self):
        """同一 cwd 总是得到同一 session_id"""
        cwd = "/home/user/project"
        assert cwd_to_session_id(cwd) == cwd_to_session_id(cwd)

    def test_cwd_to_session_id_url_safe(self):
        """session_id 是 URL 安全的（纯 hex，无 / 等特殊字符）"""
        sid = cwd_to_session_id("/home/rxx/helenagent")
        assert sid.isalnum()
        assert len(sid) == 16

    def test_cwd_to_session_id_distinct(self):
        """不同 cwd 得到不同 session_id"""
        sid1 = cwd_to_session_id("/home/user/project-a")
        sid2 = cwd_to_session_id("/home/user/project-b")
        assert sid1 != sid2
