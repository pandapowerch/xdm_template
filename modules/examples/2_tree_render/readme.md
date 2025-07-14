# 数据树渲染示例

DataHandler模块提供了数据树渲染的能力，可以将复杂的数据结构以树形方式展示。
DataHandler将解析data_config中的root_path下所有符合file_pattern的文件，并构建一个树结构。
DataDrivenGenerator将递归遍历这个树结构，并使用TemplateHander生成每个节点的渲染数据。

## 