"""File advanced operations contracts for Helen stdlib.

Defines interfaces for advanced file operations.
"""


class FileInfoContract:
    """Contract for file information operations."""

    @staticmethod
    def file_size(path: str) -> int:
        """Get file size in bytes.

        Args:
            path: File path

        Returns:
            File size in bytes

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        ...

    @staticmethod
    def file_modified(path: str) -> str:
        """Get file modification time.

        Args:
            path: File path

        Returns:
            ISO 8601 formatted datetime string

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        ...

    @staticmethod
    def list_dir(path: str, pattern: str | None = None) -> list[str]:
        """List directory contents.

        Args:
            path: Directory path
            pattern: Optional glob pattern to filter results

        Returns:
            List of file/directory names

        Raises:
            FileNotFoundError: If directory doesn't exist
            NotADirectoryError: If path is not a directory
        """
        ...

    @staticmethod
    def walk_dir(path: str) -> list[tuple[str, list[str], list[str]]]:
        """Walk directory tree.

        Args:
            path: Root directory path

        Returns:
            List of tuples (dirpath, dirnames, filenames)

        Raises:
            FileNotFoundError: If directory doesn't exist
        """
        ...


class FileOpsContract:
    """Contract for file operations."""

    @staticmethod
    def copy_file(src: str, dst: str) -> str:
        """Copy file.

        Args:
            src: Source file path
            dst: Destination file path

        Returns:
            Success message

        Raises:
            FileNotFoundError: If source doesn't exist
        """
        ...

    @staticmethod
    def move_file(src: str, dst: str) -> str:
        """Move file.

        Args:
            src: Source file path
            dst: Destination file path

        Returns:
            Success message

        Raises:
            FileNotFoundError: If source doesn't exist
        """
        ...

    @staticmethod
    def delete_file(path: str) -> str:
        """Delete file.

        Args:
            path: File path

        Returns:
            Success message

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        ...

    @staticmethod
    def delete_dir(path: str, recursive: bool = False) -> str:
        """Delete directory.

        Args:
            path: Directory path
            recursive: If True, delete recursively

        Returns:
            Success message

        Raises:
            FileNotFoundError: If directory doesn't exist
            OSError: If directory is not empty and recursive is False
        """
        ...


class TempFileContract:
    """Contract for temporary file operations."""

    @staticmethod
    def temp_file(suffix: str = "", prefix: str = "tmp", dir: str | None = None) -> str:
        """Create temporary file.

        Args:
            suffix: File suffix
            prefix: File prefix
            dir: Directory for temporary file (default: system temp dir)

        Returns:
            Path to temporary file
        """
        ...

    @staticmethod
    def temp_dir(suffix: str = "", prefix: str = "tmp", dir: str | None = None) -> str:
        """Create temporary directory.

        Args:
            suffix: Directory suffix
            prefix: Directory prefix
            dir: Directory for temporary directory (default: system temp dir)

        Returns:
            Path to temporary directory
        """
        ...
