"""
FileNode 模块
提供文件和目录节点的表示和操作。
"""

from enum import Enum
from typing import Optional, List, Dict, Any, Union, cast
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
import os


class FileType(Enum):
    FILE = "file"
    DIRECTORY = "directory"


class FilePathResolver:
    @staticmethod
    def normalize_path(path: str) -> str:
        """Normalize the file path to a standard format."""
        # 移除开头的./
        if path.startswith("./"):
            path = path[2:]
        # 标准化路径
        path = path.replace("\\", "/").strip("/")
        path = path.replace("//", "/")
        path = path.strip()
        path = path.lower()
        return path


class BaseNode:
    """节点基类，包含文件和目录共同的属性和方法"""

    def __init__(
        self, name: str, node_type: FileType, parent: Optional["DirectoryNode"] = None
    ):
        self.name = name
        self.type = node_type
        self.parent = parent

    def get_absolute_path(self) -> str:
        """获取节点的绝对路径，始终以/开头"""
        path_parts = []
        current: Optional[BaseNode] = self
        while current:
            if current.name:  # 只添加非空名称
                path_parts.append(current.name)
            current = current.parent

        # 确保返回的路径以/开头
        if not path_parts:
            return "/"
        return "/" + "/".join(reversed(path_parts))

    def get_relative_path(self, from_node: "BaseNode") -> str:
        """计算从一个节点到当前节点的相对路径"""
        # 获取两个节点的绝对路径
        from_parts = from_node.get_absolute_path().split("/")
        to_parts = self.get_absolute_path().split("/")

        # 找到公共前缀
        common_prefix_len = 0
        for i in range(min(len(from_parts), len(to_parts))):
            if from_parts[i] != to_parts[i]:
                break
            common_prefix_len = i + 1

        # 构建相对路径
        up_count = len(from_parts) - common_prefix_len
        up_path = (
            ".."
            if up_count == 1
            else "../" * (up_count - 1) + ".." if up_count > 0 else ""
        )
        down_path = "/".join(to_parts[common_prefix_len:])

        if up_path and down_path:
            return up_path + "/" + down_path
        return up_path or down_path or "."


class FileNode(BaseNode):
    """文件节点"""

    def __init__(self, file_name: str, parent: Optional["DirectoryNode"] = None):
        super().__init__(file_name, FileType.FILE, parent)

    def move_to_directory(self, directory: "DirectoryNode") -> None:
        """将文件移动到指定目录"""
        if not isinstance(directory, DirectoryNode):
            raise TypeError("Expected a DirectoryNode instance.")

        # 从原目录移除
        if self.parent:
            self.parent.children.remove(self)

        # 添加到新目录
        directory.add_child(self)


class DirectoryNode(BaseNode):
    """目录节点"""

    def __init__(self, dir_name: str, parent: Optional["DirectoryNode"] = None):
        super().__init__(dir_name, FileType.DIRECTORY, parent)
        self.children: List[Union[FileNode, "DirectoryNode"]] = []

    def add_child(self, node: Union[FileNode, "DirectoryNode"]) -> None:
        """添加子节点"""
        node.parent = self
        self.children.append(node)

    def create_file(self, file_name: str) -> FileNode:
        """创建文件节点"""
        file_node = FileNode(file_name, self)
        self.add_child(file_node)
        return file_node

    def create_directory(self, dir_name: str) -> "DirectoryNode":
        """创建子目录节点"""
        dir_node = DirectoryNode(dir_name, self)
        self.add_child(dir_node)
        return dir_node

    def build_tree(
        self, tree_path: str, patterns: Optional[Union[str, List[str]]] = None
    ) -> "DirectoryNode":
        """构建目录树"""
        if isinstance(patterns, str):
            patterns = [patterns]

        if not os.path.isdir(tree_path):
            raise ValueError(f"{tree_path} is not a valid directory path.")

        # 创建目录映射
        dir_nodes: Dict[str, DirectoryNode] = {}
        root_path = Path(tree_path).resolve()

        for root, dirs, files in os.walk(tree_path):
            current_path = Path(root).resolve()
            rel_path = current_path.relative_to(root_path)
            current_dir_path = str(rel_path)

            # 创建或获取目录节点
            if current_dir_path not in dir_nodes:
                if current_dir_path == ".":
                    current_dir = self
                else:
                    parent_path = str(rel_path.parent)
                    parent_dir = dir_nodes[parent_path]
                    current_dir = parent_dir.create_directory(rel_path.name)
                dir_nodes[current_dir_path] = current_dir
            else:
                current_dir = dir_nodes[current_dir_path]

            # 添加文件
            for filename in files:
                normalized_filename = FilePathResolver.normalize_path(filename)
                if not patterns or any(
                    fnmatch(normalized_filename, FilePathResolver.normalize_path(p))
                    for p in patterns
                ):
                    current_dir.create_file(filename)

        return self

    def find_files(self, pattern: str) -> List[FileNode]:
        """查找匹配指定模式的文件"""
        result = []
        normalized_pattern = FilePathResolver.normalize_path(pattern)

        def _traverse(node: DirectoryNode) -> None:
            for child in node.children:
                if isinstance(child, FileNode) and fnmatch(
                    FilePathResolver.normalize_path(child.name), normalized_pattern
                ):
                    result.append(child)
                elif isinstance(child, DirectoryNode):
                    _traverse(child)

        _traverse(self)
        return result

    def get_node_by_path(self, path: str) -> Optional[Union[FileNode, "DirectoryNode"]]:
        """通过路径获取节点"""
        normalized_path = FilePathResolver.normalize_path(path)
        parts = Path(normalized_path).parts
        current = self

        for part in parts[:-1]:
            found = False
            normalized_part = FilePathResolver.normalize_path(part)
            for child in current.children:
                if (
                    isinstance(child, DirectoryNode)
                    and FilePathResolver.normalize_path(child.name) == normalized_part
                ):
                    current = child
                    found = True
                    break
            if not found:
                return None

        target = FilePathResolver.normalize_path(parts[-1])
        for child in current.children:
            if FilePathResolver.normalize_path(child.name) == target:
                return child

        return None

    def serialize_tree(self, indent: int = 0) -> str:
        """序列化目录树为字符串"""
        result = [" " * indent + self.name + "/"]

        for child in self.children:
            if isinstance(child, DirectoryNode):
                result.append(child.serialize_tree(indent + 2))
            else:
                result.append(" " * (indent + 2) + child.name)

        return "\n".join(result)
