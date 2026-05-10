# 基于大语言模型的知识图谱驱动课件自动生成平台

## 项目简介

随着大语言模型如 DeepSeek 的广泛应用，其在自然语言理解、文本生成与结构抽取等方面展现出卓越能力，为教学智能化提供了技术基础。结合知识图谱对知识结构关系的建模能力，本项目拟构建一个“基于大语言模型的知识图谱驱动课件自动生成平台”，以“高效、系统、智能”为目标，为教师提供全流程、结构化的智能备课支持工具。

本项目的核心思路是：以自然语言形式的教学文稿或教材章节为输入，调用大语言模型自动抽取核心知识点，构建知识图谱结构；再以图谱为依托，自动生成课程讲解稿、PPT 提纲、习题题目与参考答案，实现从知识理解到教学设计的全链条智能支持。

## 多用户与数据存储

应用侧边栏可以选择已有用户或新建用户。每个用户拥有独立的 Prompt 模板配置、历史知识点和知识图谱记录，适合多位教师在同一套本地应用中分别维护自己的备课习惯与生成结果。

用户数据保存在 `data/users/<user_id>/` 下：

- `profile.json`：用户基础信息。
- `prompt_templates.json`：该用户自己的 Prompt 模板。
- `knowledge_graphs.json`：该用户确认保存过的知识点、知识图谱关系和原文摘录。

`data/` 已加入 `.gitignore`，不会随项目代码提交到 GitHub。当前实现是本地用户名隔离，不包含密码登录和权限控制；如果部署到公网环境，建议继续增加认证、权限和数据库存储。

## Prompt 模板配置

`prompt_templates.json` 是新用户初始化时使用的默认 Prompt 模板。用户可以在应用侧边栏进入“Prompt 模板配置”页面修改自己的模板，保存后只影响当前用户。

- `system_prompt`：模型系统提示词。
- `knowledge_extraction`：知识点抽取模板，支持 `{{text}}` 占位符。
- `graph_edges`：知识关系与关联原因抽取模板，支持 `{{name_list}}`、`{{text}}` 占位符。
- `node_content`：节点讲义生成模板，支持 `{{name}}`、`{{definition}}` 占位符。

## 运行说明

应用支持上传 TXT、DOCX 和 PDF 教学文档。PDF 解析依赖文本层，扫描版 PDF 暂不支持自动 OCR。

DeepSeek API Key 放在本地 `config.json` 中，不要提交到仓库。可参考 `config.example.json`：

- `DEEPSEEK_API_KEY`：DeepSeek API Key。
- `DEEPSEEK_USE_ENV_PROXY`：是否继承系统代理环境变量，默认建议为 `false`。
- `DEEPSEEK_PROXY`：需要显式代理时填写，例如 `http://127.0.0.1:7890`，不需要则留空。

知识图谱前端渲染依赖 Cytoscape，当前通过 unpkg CDN 加载。运行应用时需要能访问 `https://unpkg.com/cytoscape@3.23.0/dist/cytoscape.min.js`；如果部署在离线或校园内网环境，建议将 Cytoscape 前端库下载到本地并修改 `templates/graph.html` 中的脚本地址。
