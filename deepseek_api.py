# deepseek_api.py
import os
import requests
import json
import logging
import re
from prompt_config import get_prompt_template, render_prompt, render_prompt_template

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
API_URL = "https://api.deepseek.com/v1/chat/completions"
REQUEST_TIMEOUT = (10, 60)
logger = logging.getLogger(__name__)

def _load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as config_file:
            return json.load(config_file)
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("配置文件读取失败：%s", e)
        return {}

def _get_api_key():
    config = _load_config()
    return config.get("DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_API_KEY")

def _build_headers(api_key):
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

def parse_json_array(raw):
    if not raw or not raw.strip():
        raise ValueError("模型返回为空")

    candidates = [raw.strip()]
    fenced_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)```", raw, flags=re.IGNORECASE)
    candidates.extend(block.strip() for block in fenced_blocks if block.strip())

    decoder = json.JSONDecoder()
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                for key in ("data", "items", "nodes", "edges", "relations"):
                    if isinstance(parsed.get(key), list):
                        return parsed[key]
        except json.JSONDecodeError:
            pass

        for start_index, char in enumerate(candidate):
            if char != "[":
                continue
            try:
                parsed, _ = decoder.raw_decode(candidate[start_index:])
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, list):
                return parsed

    raise ValueError("未找到合法的 JSON 数组")

def _call_deepseek(prompt):
    api_key = _get_api_key()
    if not api_key:
        logger.warning("未配置 DeepSeek API Key，请在 config.json 中设置 DEEPSEEK_API_KEY。")
        return ""

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": get_prompt_template("system_prompt")},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5
    }
    try:
        response = requests.post(
            API_URL,
            headers=_build_headers(api_key),
            json=payload,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        response_data = response.json()
        content = response_data["choices"][0]["message"]["content"]
        logger.debug("模型原始返回：%s", content[:500])
        return content
    except requests.Timeout:
        logger.warning("API 调用超时，请检查网络或稍后重试。")
        return ""
    except requests.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else "未知"
        logger.warning("API HTTP 错误：%s，请检查 API Key、额度或请求内容。", status_code)
        return ""
    except (KeyError, IndexError, ValueError) as e:
        logger.warning("API 响应格式异常：%s", e)
        return ""
    except requests.RequestException as e:
        logger.warning("API 网络请求失败：%s", e)
        return ""
    except Exception as e:
        logger.exception("API 调用失败：%s", e)
        return ""

def extract_knowledge(text):
    raw = _call_deepseek(text)
    try:
        parsed = parse_json_array(raw)
        logger.debug("知识点解析成功：%s", parsed)
        return parsed
    except Exception as e:
        logger.warning("知识点 JSON 解析失败：%s", e)
        return []

def infer_relation_type(reason):
    reason = str(reason or "")
    relation_rules = [
        ("前置基础", ("基础", "前提", "先修", "理解", "支撑", "依赖", "铺垫")),
        ("应用扩展", ("应用", "场景", "扩展", "实践", "用于", "案例")),
        ("因果关系", ("导致", "影响", "决定", "产生", "原因", "结果", "推导")),
        ("组成关系", ("组成", "包含", "部分", "构成", "包括")),
        ("对比关系", ("区别", "比较", "相对", "不同", "对比")),
    ]
    for relation_type, keywords in relation_rules:
        if any(keyword in reason for keyword in keywords):
            return relation_type
    return "相关联系"

def generate_graph_edges(text, node_names):
    name_list = "，".join(node_names)
    prompt = render_prompt_template("graph_edges", name_list=name_list, text=text)
    raw = _call_deepseek(prompt)
    valid_names = set(node_names)
    edges = []

    try:
        parsed = parse_json_array(raw)
        for item in parsed:
            if not isinstance(item, dict):
                continue
            source = str(item.get("source", "")).strip()
            target = str(item.get("target", "")).strip()
            reason = str(item.get("reason", "")).strip()
            relation_type = str(item.get("relation_type", "")).strip()
            if source in valid_names and target in valid_names and source != target:
                edges.append({
                    "source": source,
                    "target": target,
                    "relation_type": relation_type or infer_relation_type(reason),
                    "reason": reason or "二者在教学内容中存在直接知识联系"
                })
        return edges
    except Exception as e:
        logger.warning("关系原因 JSON 解析失败，尝试按文本格式解析：%s", e)

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
                "relation_type": infer_relation_type(reason),
                "reason": reason
            })
    return edges

def generate_node_content(name, definition="", template=""):
    prompt_template = template or get_prompt_template("node_content")
    prompt = render_prompt(prompt_template, name=name, definition=definition)
    return _call_deepseek(prompt)
