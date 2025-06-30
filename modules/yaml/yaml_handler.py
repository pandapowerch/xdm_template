import yaml
from typing import Optional, List, Dict, Any, Iterator
from dataclasses import dataclass
from pathlib import Path

from ..node.data_node import DataNode
from ..node.file_node import DirectoryNode, FileNode

@dataclass
class YamlConfig:
    """YAML configuration with preserved keys for template and children paths"""

    root_path: Path
    encoding: str = "utf-8"
    # These keys are moved from DataDrivenGeneratorConfig since they are specific to YAML data handling
    preserved_template_key: str = "TEMPLATE_PATH"
    preserved_children_key: str = "CHILDREN_PATH"

    @classmethod
    def validate(cls, config: Dict[str, Any]) -> "YamlConfig":
        """Validate configuration and return config object

        Args:
            config: Dictionary containing configuration values.
                Required:
                    - root_path: Path to the root YAML file
                Optional:
                    - encoding: File encoding (default: utf-8)
                    - preserved_template_key: Key for template path (default: TEMPLATE_PATH)
                    - preserved_children_key: Key for children (default: CHILDREN_PATH)
        """
        if "root_path" not in config:
            raise ValueError("Missing required field 'root_path'")

        root_path = Path(config["root_path"])
        if not root_path.exists():
            raise ValueError(f"root_path {root_path} does not exist")

        return cls(
            root_path=root_path,
            encoding=config.get("encoding", "utf-8"),
            preserved_template_key=config.get(
                "preserved_template_key", "TEMPLATE_PATH"
            ),
            preserved_children_key=config.get(
                "preserved_children_key", "CHILDREN_PATH"
            ),
        )


class YamlFileHandler:
    @staticmethod
    def load_yaml_file(yaml_path: str) -> dict:
        """Load a YAML file and return its contents as a dictionary."""
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data if data is not None else {}
        except Exception as e:
            print(f"Error loading YAML file {yaml_path}: {e}")
            return {}


class YamlDataTreeHandler:
    """Handler for YAML data trees that implement DataHandler protocol"""

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize the handler with configuration"""
        self.config = YamlConfig.validate(config)
        # Initialize the yaml file tree with a root node
        self.file_tree: DirectoryNode = DirectoryNode(dir_name=self.config.root_path.name)
        self.file_tree_init()
        # Initilaze the data tree with a root node
        self.data_tree: DataNode = DataNode(data=None, name=self.config.root_path.name)
        self.data_tree_init()

    @property
    def preserved_template_key(self) -> str:
        """Get preserved template key from config"""
        return self.config.preserved_template_key

    @property
    def preserved_children_key(self) -> str:
        """Get preserved children key from config"""
        return self.config.preserved_children_key

    def file_tree_init(self) -> None:
        """Initialize the file tree from the YAML file"""
        self.file_tree.build_tree(str(self.config.root_path), patterns=["*.yaml"])

    def data_tree_init(self) -> None:
        # TODO: Implement the data tree initialization
        def _get_children_paths(node: DirectoryNode) -> List[str]:
            """Recursively get all child paths in the directory node"""
            paths = []
            for child in node.children:
                if isinstance(child, DirectoryNode):
                    paths.append(str(child.get_absolute_path()))
                    paths.extend(_get_children_paths(child))
            return paths
        """Initialize the data tree from the YAML file"""
        for child in self.file_tree.children:
            if isinstance(child, FileNode):
                # Create a DataNode for each directory
                # Read the YAML file and create a DataNode with its data
                yaml_data = YamlFileHandler.load_yaml_file(str(child.get_absolute_path()))
                data_node = DataNode(data=yaml_data, name=child.name)
                self.data_tree.add_child(data_node)
                

    def get_data(self) -> Iterator[Dict[str, Any]]:
        """Get data iterator, yielding each node's data from the tree"""
        # This is a placeholder implementation
        # In practice, this should traverse the data tree and yield each node's data

        data = self.load_yaml_file(str(self.config.root_path))
        yield data
