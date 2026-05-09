# deepseek_api.py
import os
import requests
import json
import re

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def _load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as config_file:
            return json.load(config_file)
    except (OSError, json.JSONDecodeError) as e:
        print("❌ 配置文件读取失败：", e)
        return {}

CONFIG = _load_config()
DEEPSEEK_API_KEY = CONFIG.get("DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
API_URL = "https://api.deepseek.com/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    "Content-Type": "application/json"
}

def _call_deepseek(prompt):
    if not DEEPSEEK_API_KEY:
        print("❌ 未配置 DeepSeek API Key，请在 config.json 中设置 DEEPSEEK_API_KEY。")
        return ""

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是教学专家，擅长知识提取和结构化讲解。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5
    }
    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        print("📌 模型原始返回：", content[:500])
        return content
    except Exception as e:
        print("❌ API 调用失败：", e)
        return ""

def extract_knowledge(text):
    raw = _call_deepseek(text)
    try:
        match = re.search(r"\[\s*{.*?}\s*\]", raw, re.DOTALL)
        json_text = match.group(0) if match else raw
        parsed = json.loads(json_text)
        print("📌 解析成功：", parsed)
        return parsed
    except Exception as e:
        print("❌ JSON解析失败：", e)
        return []

def generate_graph_edges(text, node_names):
    name_list = "，".join(node_names)
    prompt = f"""请提取以下术语之间的知识关系，并说明每条关系成立的原因。

要求：
1. 只使用术语列表中的原词作为 source 和 target。
2. reason 要解释两个知识点为什么相连，便于学生理解知识点之间的联系。
3. reason 控制在 15~50 个中文字符。
4. 严格输出 JSON 数组，不要输出 Markdown、编号或额外说明。

输出格式示例：
[
  {{"source": "术语A", "target": "术语B", "reason": "术语A是理解术语B的基础概念"}},
  {{"source": "术语B", "target": "术语C", "reason": "术语C是在术语B基础上的进一步应用"}}
]

术语列表：{name_list}

教学内容：
{text}
"""
    raw = _call_deepseek(prompt)
    valid_names = set(node_names)
    edges = []

    try:
        match = re.search(r"\[\s*{.*?}\s*\]", raw, re.DOTALL)
        json_text = match.group(0) if match else raw
        parsed = json.loads(json_text)
        for item in parsed:
            if not isinstance(item, dict):
                continue
            source = str(item.get("source", "")).strip()
            target = str(item.get("target", "")).strip()
            reason = str(item.get("reason", "")).strip()
            if source in valid_names and target in valid_names and source != target:
                edges.append({
                    "source": source,
                    "target": target,
                    "reason": reason or "二者在教学内容中存在直接知识联系"
                })
        return edges
    except Exception as e:
        print("❌ 关系原因 JSON 解析失败，尝试按文本格式解析：", e)

    for line in raw.split("\n"):
        if "→" not in line:
            continue
        a, b = line.strip().split("→", 1)
        a_clean = re.sub(r"^\s*\d+[\.．、\-\)]*\s*", "", a.strip())
        b_parts = re.split(r"\s*[：:，,；;]\s*", b.strip(), maxsplit=1)
        b_clean = re.sub(r"^\s*\d+[\.．、\-\)]*\s*", "", b_parts[0].strip())
        reason = b_parts[1].strip() if len(b_parts) > 1 else "二者在教学内容中存在直接知识联系"
        if a_clean in valid_names and b_clean in valid_names and a_clean != b_clean:
            edges.append({
                "source": a_clean,
                "target": b_clean,
                "reason": reason
            })
    return edges

def generate_node_content(concept):
    prompt = f"请为教学术语“{concept}”生成教学讲义草稿，包含：概念定义、公式推导、应用示例、常见误区。格式用 Markdown 书写。"
    return _call_deepseek(prompt)
