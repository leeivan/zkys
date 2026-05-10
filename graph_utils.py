# graph_utils.py
import hashlib
import json
import logging
import os
from pathlib import Path

import streamlit as st

logger = logging.getLogger(__name__)

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "templates", "graph.html")
RUNTIME_GRAPH_DIR = os.path.join(os.path.dirname(__file__), "data", "runtime_graphs")

def _text_width(text):
    return sum(2 if ord(char) > 127 else 1 for char in text)

def _node_dimensions(label):
    width = min(max(104, _text_width(label) * 8 + 36), 220)
    height = 48 if width < 160 else 62
    return width, height

def _infer_relation_type(reason):
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

def _edge_fields(edge):
    if isinstance(edge, dict):
        source = edge.get("source") or edge.get("from") or edge.get("src") or ""
        target = edge.get("target") or edge.get("to") or edge.get("dst") or ""
        reason = edge.get("reason") or edge.get("label") or edge.get("relation") or ""
        relation_type = edge.get("relation_type") or edge.get("type") or ""
        return (
            str(source).strip(),
            str(target).strip(),
            str(reason).strip(),
            str(relation_type).strip() or _infer_relation_type(reason),
        )

    if not isinstance(edge, (list, tuple)):
        return "", "", "", ""

    source = str(edge[0]).strip() if len(edge) >= 1 else ""
    target = str(edge[1]).strip() if len(edge) >= 2 else ""
    reason = str(edge[2]).strip() if len(edge) >= 3 else ""
    relation_type = str(edge[3]).strip() if len(edge) >= 4 else ""

    return source, target, reason, relation_type or _infer_relation_type(reason)

def _load_graph_template():
    try:
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as template_file:
            return template_file.read()
    except OSError as e:
        logger.error("图谱模板读取失败：%s", e)
        return "<p>图谱模板读取失败，请检查 templates/graph.html。</p>"

def _render_graph_html(elements_json, node_count, edge_count):
    return (
        _load_graph_template()
        .replace("__ELEMENTS_JSON__", elements_json)
        .replace("__NODE_COUNT__", str(node_count))
        .replace("__EDGE_COUNT__", str(edge_count))
    )

def _write_runtime_graph_html(html_content):
    os.makedirs(RUNTIME_GRAPH_DIR, exist_ok=True)
    content_hash = hashlib.sha256(html_content.encode("utf-8")).hexdigest()[:16]
    graph_path = os.path.join(RUNTIME_GRAPH_DIR, f"graph_{content_hash}.html")

    if not os.path.exists(graph_path):
        with open(graph_path, "w", encoding="utf-8") as graph_file:
            graph_file.write(html_content)

    return Path(graph_path)

def visualize_graph(nodes, edges):
    logger.debug("图谱节点：%s", nodes)
    logger.debug("图谱边：%s", edges)

    node_ids = set()
    elements = []
    in_degree = {}
    out_degree = {}

    for node in nodes:
        node_id = node["name"]
        node_ids.add(node_id)
        in_degree[node_id] = 0
        out_degree[node_id] = 0

    unique_edges = []
    seen_edges = set()
    for edge in edges:
        src, dst, reason, relation_type = _edge_fields(edge)
        edge_key = (src, dst)
        if src in node_ids and dst in node_ids and edge_key not in seen_edges:
            seen_edges.add(edge_key)
            unique_edges.append({
                "source": src,
                "target": dst,
                "relation_type": relation_type,
                "reason": reason or "二者在教学内容中存在直接知识联系",
            })
            out_degree[src] += 1
            in_degree[dst] += 1

    for node in nodes:
        node_id = node["name"]
        label = str(node_id)
        definition = str(node.get("definition", "")).strip()
        width, height = _node_dimensions(label)
        degree = in_degree[node_id] + out_degree[node_id]
        classes = []
        if degree == 0:
            classes.append("isolated")
        elif in_degree[node_id] == 0:
            classes.append("root")
        elif out_degree[node_id] == 0:
            classes.append("leaf")
        if degree >= 3:
            classes.append("hub")

        elements.append({
            "data": {
                "id": node_id,
                "label": label,
                "definition": definition or "暂无定义",
                "inDegree": in_degree[node_id],
                "outDegree": out_degree[node_id],
                "width": width,
                "height": height,
                "textMaxWidth": max(width - 26, 80),
            },
            "classes": " ".join(classes),
        })

    for index, edge in enumerate(unique_edges):
        elements.append({
            "data": {
                "id": f"edge-{index}",
                "source": edge["source"],
                "target": edge["target"],
                "relationType": edge["relation_type"],
                "reason": edge["reason"],
                "relationTitle": f"{edge['source']} → {edge['target']}",
            }
        })

    elements_json = json.dumps(elements, ensure_ascii=False).replace("</", "<\\/")
    logger.debug("图谱可视化元素：%s", elements_json[:300])

    html_content = _render_graph_html(elements_json, len(nodes), len(unique_edges))
    st.iframe(_write_runtime_graph_html(html_content), width="stretch", height=720)
