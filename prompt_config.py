# prompt_config.py
import json
import logging
import os

PROMPT_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "prompt_templates.json")
logger = logging.getLogger(__name__)

DEFAULT_PROMPT_TEMPLATES = {
    "system_prompt": "你是教学专家，擅长知识提取、知识关系分析和结构化教学内容生成。",
    "knowledge_extraction": (
        "请从以下教学内容中提取 3~7 个核心知识点。每个知识点包含 name 和 definition 两个字段。\n"
        "严格输出为 JSON 格式，例如：\n"
        "[\n"
        "  {\"name\": \"术语A\", \"definition\": \"简要定义\"},\n"
        "  {\"name\": \"术语B\", \"definition\": \"简要定义\"}\n"
        "]\n\n"
        "教学内容如下：\n"
        "{{text}}"
    ),
    "graph_edges": (
        "请提取以下术语之间的知识关系，并说明每条关系成立的原因。\n\n"
        "要求：\n"
        "1. 只使用术语列表中的原词作为 source 和 target。\n"
        "2. relation_type 表示关系类型，从“前置基础、应用扩展、因果关系、组成关系、对比关系、相关联系”中选择一个。\n"
        "3. reason 要解释两个知识点为什么相连，便于学生理解知识点之间的联系。\n"
        "4. reason 控制在 15~50 个中文字符。\n"
        "5. 严格输出 JSON 数组，不要输出 Markdown、编号或额外说明。\n\n"
        "输出格式示例：\n"
        "[\n"
        "  {\"source\": \"术语A\", \"target\": \"术语B\", \"relation_type\": \"前置基础\", \"reason\": \"术语A是理解术语B的基础概念\"},\n"
        "  {\"source\": \"术语B\", \"target\": \"术语C\", \"relation_type\": \"应用扩展\", \"reason\": \"术语C是在术语B基础上的进一步应用\"}\n"
        "]\n\n"
        "术语列表：{{name_list}}\n\n"
        "教学内容：\n"
        "{{text}}"
    ),
    "node_content": (
        "## {{name}}\n\n"
        "### 定义\n"
        "{{definition}}\n\n"
        "### 推导或背景知识\n"
        "请补充详细公式或理论支撑。\n\n"
        "### 应用场景或案例\n"
        "请给出典型教学例子。\n\n"
        "### 常见误区\n"
        "列出 1-2 个典型误解。"
    ),
}

def get_prompt_templates():
    templates = DEFAULT_PROMPT_TEMPLATES.copy()
    if not os.path.exists(PROMPT_TEMPLATE_PATH):
        return templates

    try:
        with open(PROMPT_TEMPLATE_PATH, "r", encoding="utf-8") as config_file:
            user_templates = json.load(config_file)
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Prompt 模板配置文件读取失败：%s", e)
        return templates

    if not isinstance(user_templates, dict):
        logger.warning("Prompt 模板配置必须是 JSON 对象。")
        return templates

    for key, value in user_templates.items():
        if isinstance(value, str):
            templates[key] = value
    return templates

def get_prompt_template(name):
    return get_prompt_templates().get(name, DEFAULT_PROMPT_TEMPLATES.get(name, ""))

def save_prompt_templates(templates):
    saved_templates = DEFAULT_PROMPT_TEMPLATES.copy()
    for key in DEFAULT_PROMPT_TEMPLATES:
        value = templates.get(key, "")
        if isinstance(value, str) and value.strip():
            saved_templates[key] = value

    with open(PROMPT_TEMPLATE_PATH, "w", encoding="utf-8") as config_file:
        json.dump(saved_templates, config_file, ensure_ascii=False, indent=2)
        config_file.write("\n")

    return saved_templates

def render_prompt(template, **values):
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", str(value))
    return rendered

def render_prompt_template(name, **values):
    return render_prompt(get_prompt_template(name), **values)

def render_text_prompt(template, text):
    if "{{text}}" in template:
        return render_prompt(template, text=text)
    return f"{template.strip()}\n\n{text.strip()}"
