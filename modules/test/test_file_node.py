"""Test cases for file_node module"""
import os
import tempfile
import unittest
from pathlib import Path
from fnmatch import fnmatch

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from modules.node.file_node import DirectoryNode, FileNode, FilePathResolver, BaseNode

class TestFileNode(unittest.TestCase):
    def setUp(self):
        """Create a temporary directory structure for testing"""
        self.test_dir = tempfile.mkdtemp()
        
        # Create test directory structure
        self.create_test_files([
            "config.yaml",
            "test.json",
            "vars/var1.yaml",
            "vars/var2.yaml",
            "vars/data.json",
            "nested/deep/file.yaml"
        ])
        
        # Create root node
        self.root = DirectoryNode("")

    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        shutil.rmtree(self.test_dir)

    def create_test_files(self, paths):
        """Helper method to create test files"""
        for path in paths:
            full_path = os.path.join(self.test_dir, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                f.write(f"Test content for {path}")

    def test_file_path_resolver(self):
        """Test FilePathResolver functionality"""
        tests = [
            ("path/to/file.yaml", "path/to/file.yaml"),
            ("path\\to\\file.yaml", "path/to/file.yaml"),
            ("PATH/TO/FILE.YAML", "path/to/file.yaml"),
            ("//path//to//file.yaml", "path/to/file.yaml"),
            ("  path/to/file.yaml  ", "path/to/file.yaml"),
            ("./path/to/file.yaml", "path/to/file.yaml")
        ]
        
        for input_path, expected in tests:
            self.assertEqual(
                FilePathResolver.normalize_path(input_path),
                expected
            )

    def test_base_node_functionality(self):
        """Test BaseNode functionality for both file and directory nodes"""
        # Create nodes
        root = DirectoryNode("")
        dir_node = root.create_directory("test_dir")
        file_node = dir_node.create_file("test.txt")
        
        # Test inheritance
        self.assertTrue(isinstance(dir_node, BaseNode))
        self.assertTrue(isinstance(file_node, BaseNode))
        
        # Test basic properties
        self.assertEqual(dir_node.name, "test_dir")
        self.assertEqual(file_node.name, "test.txt")
        
        # Test paths from base class method
        self.assertEqual(dir_node.get_absolute_path(), "/test_dir")
        self.assertEqual(file_node.get_absolute_path(), "/test_dir/test.txt")
        
        # Test relative path calculation from base class
        # 从root到file_node的相对路径
        to_file = file_node.get_relative_path(root)
        self.assertEqual(to_file, "../test_dir/test.txt")
        
        # 从file_node到dir_node的相对路径
        to_dir = dir_node.get_relative_path(file_node)
        self.assertEqual(to_dir, "..")
        
        # 从dir_node到root的相对路径
        to_root = root.get_relative_path(dir_node)
        self.assertEqual(to_root, "..")

    def test_directory_operations(self):
        """Test directory-specific operations"""
        # Create directory structure
        vars_dir = self.root.create_directory("vars")
        config_file = vars_dir.create_file("config.yaml")
        
        # Test structure
        self.assertTrue(isinstance(vars_dir, DirectoryNode))
        self.assertTrue(isinstance(config_file, FileNode))
        self.assertEqual(vars_dir.name, "vars")
        self.assertEqual(config_file.name, "config.yaml")
        
        # Test parent-child relationships
        self.assertEqual(config_file.parent, vars_dir)
        self.assertIn(config_file, vars_dir.children)

        # Test absolute paths
        self.assertEqual(vars_dir.get_absolute_path(), "/vars")
        self.assertEqual(config_file.get_absolute_path(), "/vars/config.yaml")

    def test_file_movement(self):
        """Test file movement between directories"""
        # Create initial structure
        vars_dir = self.root.create_directory("vars")
        new_dir = self.root.create_directory("new_dir")
        config_file = vars_dir.create_file("config.yaml")
        
        # Test initial state
        self.assertEqual(config_file.parent, vars_dir)
        self.assertEqual(config_file.get_absolute_path(), "/vars/config.yaml")
        
        # Move file
        config_file.move_to_directory(new_dir)
        
        # Test final state
        self.assertEqual(config_file.parent, new_dir)
        self.assertEqual(config_file.get_absolute_path(), "/new_dir/config.yaml")
        self.assertNotIn(config_file, vars_dir.children)

    def test_file_tree_build(self):
        """Test file tree building"""
        # Build tree with pattern
        self.root.build_tree(self.test_dir, "*.yaml")
        
        # 验证目录结构
        self.assertTrue(any(f.name == "var1.yaml" for f in self.root.find_files("*.yaml")))
        self.assertFalse(any(f.name == "data.json" for f in self.root.find_files("*.yaml")))
        
        # 验证深层目录
        nested_yaml = self.root.get_node_by_path("nested/deep/file.yaml")
        self.assertIsNotNone(nested_yaml)
        self.assertEqual(nested_yaml.get_absolute_path(), "/nested/deep/file.yaml")

    def test_relative_paths(self):
        """Test relative path calculations"""
        # 创建嵌套目录结构
        vars_dir = self.root.create_directory("vars")
        nested = self.root.create_directory("nested")
        deep = nested.create_directory("deep")
        
        # 创建文件
        var1 = vars_dir.create_file("var1.yaml")
        deep_file = deep.create_file("file.yaml")
        
        # 测试相对路径
        rel_path = deep.get_relative_path(vars_dir)
        self.assertEqual(rel_path, "../nested/deep")
        
        # 测试绝对路径
        self.assertEqual(var1.get_absolute_path(), "/vars/var1.yaml")
        self.assertEqual(deep_file.get_absolute_path(), "/nested/deep/file.yaml")

    def test_path_finding(self):
        """Test path finding with different formats"""
        self.root.build_tree(self.test_dir)
        
        # 测试不同路径格式
        paths = [
            ("vars/var1.yaml", True),
            ("VARS/VAR1.YAML", True),      # 大写路径
            ("vars\\var1.yaml", True),     # Windows路径
            ("./vars/var1.yaml", True),    # 相对路径
            ("non/existent.yaml", False)   # 不存在的路径
        ]
        
        for path, should_exist in paths:
            node = self.root.get_node_by_path(path)
            if should_exist:
                self.assertIsNotNone(node, f"Should find node: {path}")
                self.assertTrue(node.get_absolute_path().startswith("/"))
                self.assertEqual(
                    FilePathResolver.normalize_path(node.name),
                    "var1.yaml"
                )
            else:
                self.assertIsNone(node, f"Should not find node: {path}")

    def test_root_path(self):
        """Test root directory path handling"""
        # 测试空目录名的根节点
        root = DirectoryNode("")
        self.assertEqual(root.get_absolute_path(), "/")
        
        # 测试有名字的根节点
        root = DirectoryNode("root")
        self.assertEqual(root.get_absolute_path(), "/root")

if __name__ == '__main__':
    unittest.main()
