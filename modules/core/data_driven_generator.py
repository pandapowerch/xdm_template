"""Data-driven generator module for Jinja Template"""

from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from . import (
    GeneratorError,
    GeneratorErrorType,
    DataHandler,
    TemplateHandler,
    validate_data_context,
    validate_render_result,
)
from .handler_factory import HandlerFactory
from .types import DataHandlerType, TemplateHandlerType
from ..node.data_node import DataNode
from ..jinja.user_func.func_handler import UserFunctionInfo, UserFunctionResolver


@dataclass
class DataDrivenGeneratorConfig:
    """Configuration for the DataDrivenGenerator"""

    data_type: DataHandlerType
    data_config: Dict[str, Any]
    template_type: TemplateHandlerType
    template_config: Dict[str, Any]


class DataDrivenGenerator:
    """Data-driven generator class
    This class is responsible for generating data-driven templates based on provided data.
    """

    def __init__(self, config: DataDrivenGeneratorConfig) -> None:
        """Initialize the generator with configuration

        Args:
            config: Configuration for data and template handlers
        """
        self.data_handler = HandlerFactory.create_data_handler(
            config.data_type, config.data_config
        )
        self.template_handler = HandlerFactory.create_template_handler(
            config.template_type, config.template_config
        )
        # 存储渲染结果的映射
        self._rendered_contents: Dict[DataNode, str] = {}

    def render(self, pattern: str) -> Dict[str, str]:
        """渲染模板并返回结果

        Args:
            pattern: 用于查找数据文件的模式，如 "root.yaml"

        Returns:
            Dict[str, str]: 文件名到渲染结果的映射

        Raises:
            GeneratorError: 如果数据验证或渲染失败
        """
        # 清空之前的渲染结果
        self._rendered_contents.clear()
        results = {}

        # 1. 创建数据树
        trees = self.data_handler.create_data_tree(pattern)
        if not trees:
            raise GeneratorError(
                GeneratorErrorType.DATA_INIT_ERROR,
                f"No data files found matching pattern: {pattern}",
            )

        # 2. 对每个树进行后序遍历和渲染
        for tree in trees:
            self._process_node(tree)
            key = f"{tree.name}"
            results[key] = self._rendered_contents[tree]

        if not results:
            raise GeneratorError(
                GeneratorErrorType.RENDER_ERROR, "No templates were rendered"
            )

        return results

    def _process_node(self, node: DataNode) -> None:
        """处理单个节点及其子节点

        采用后序遍历（先处理子节点再处理父节点）

        Args:
            node: 要处理的数据节点
        """
        # 1. 先处理所有子节点
        for child in node.children:
            if isinstance(child, DataNode):
                self._process_node(child)

        # 2. 验证数据
        validate_data_context(node.data, self.data_handler.preserved_template_key)

        # 3. 准备渲染上下文
        data = node.data

        # 4. 收集子节点渲染结果
        children_content: List[str] = []
        for child in node.children:
            if isinstance(child, DataNode) and child in self._rendered_contents:
                children_content.append(self._rendered_contents[child])

        # 5. 添加子节点内容到上下文
        data[self.template_handler.config.preserved_children_key] = "\n".join(
            children_content
        )

        try:
            # Dynamic create resolver for DataNode
            node_resolver = self._create_node_resolver(node)

            from ..jinja.expr_filter import expr_filter_factory

            # Currently only create expr filter
            # TODO: Maybe need extent?
            filters = {"expr_filter": expr_filter_factory(node_resolver)}

            # 6. 渲染模板
            template_path = node.data[self.data_handler.preserved_template_key]
            result = self.template_handler.render_template(
                template_path, data, filters=filters
            )

            # 7. 验证结果并保存
            validate_render_result(result, template_path)
            self._rendered_contents[node] = result

        except Exception as e:
            raise GeneratorError(
                GeneratorErrorType.RENDER_ERROR,
                f"Failed to render {template_path}: {str(e)}",
            )

    def _create_node_resolver(self, node: DataNode) -> UserFunctionResolver:
        """为当前节点创建独立的函数解析器

        Args:
            node: 当前处理的节点

        Returns:
            UserFunctionResolver: 节点特定的函数解析器
        """
        # 1. 创建节点特定的函数列表
        node_functions = [
            # 基本节点信息函数
            UserFunctionInfo(
                name="node:name",
                arg_range=[0, 0],
                description="Get current node name",
                handler=lambda: node.name,
            ),
            UserFunctionInfo(
                name="node:path",
                arg_range=[0, 0],
                description="Get node depth in the tree",
                handler=lambda: node.get_absolute_path(),
            ),
            UserFunctionInfo(
                name="node:get_rel",
                arg_range=[1, 1],
                description="Get node depth in the tree",
                handler=lambda x: node.get_node_by_path(x),
            ),
            UserFunctionInfo(
                name="node:get_name",
                arg_range=[0, 1],
                description="Get node depth in the tree",
                handler=lambda x=None: str(node.name) if x is None else x.name,
            ),
            # 示例函数：双倍值
            UserFunctionInfo(
                name="user:double",
                arg_range=[1, 1],
                description="Double the input value",
                handler=lambda x: 2 * x.value,
            ),
        ]

        # # 2. 添加节点数据相关函数
        # if "value" in node.data:
        #     node_functions.append(
        #         UserFunctionInfo(
        #             name="data:value",
        #             arg_range=[0, 0],
        #             description="Get node's value",
        #             handler=lambda: node.data["value"],
        #         )
        #     )

        # # 3. 添加子节点相关函数
        # if node.children:
        #     node_functions.extend(
        #         [
        #             UserFunctionInfo(
        #                 name="children:count",
        #                 arg_range=[0, 0],
        #                 description="Get children count",
        #                 handler=lambda: len(node.children),
        #             ),
        #             UserFunctionInfo(
        #                 name="children:names",
        #                 arg_range=[0, 0],
        #                 description="Get children names",
        #                 handler=lambda: [
        #                     c.name for c in node.children if isinstance(c, DataNode)
        #                 ],
        #             ),
        #         ]
        #     )

        # 4. 创建并返回解析器
        return UserFunctionResolver(node_functions)
