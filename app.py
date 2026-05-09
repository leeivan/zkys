import streamlit as st
from deepseek_api import extract_knowledge, generate_graph_edges, generate_node_content
from graph_utils import visualize_graph
from prompt_config import (
    DEFAULT_PROMPT_TEMPLATES,
    get_prompt_templates,
    render_prompt_template,
    save_prompt_templates,
)

st.set_page_config(page_title="知识图谱自动生成演示平台", layout="wide")
st.title("📚 知识图谱自动生成演示平台")

def _as_records(rows):
    if rows is None:
        return []
    if hasattr(rows, "to_dict"):
        return rows.to_dict("records")
    return list(rows)

def _validate_nodes(rows):
    nodes = []
    errors = []
    seen_names = set()

    for index, row in enumerate(_as_records(rows), start=1):
        if not isinstance(row, dict):
            errors.append(f"第 {index} 行不是有效的知识点记录")
            continue

        name_value = row.get("name", "")
        definition_value = row.get("definition", "")
        name = "" if name_value is None else str(name_value).strip()
        definition = "" if definition_value is None else str(definition_value).strip()

        if not name:
            errors.append(f"第 {index} 行缺少 name")
            continue
        if name in seen_names:
            errors.append(f"知识点名称重复：{name}")
            continue

        seen_names.add(name)
        nodes.append({"name": name, "definition": definition})

    return nodes, errors

def _edge_to_row(edge):
    if isinstance(edge, dict):
        return {
            "起点": edge.get("source", ""),
            "终点": edge.get("target", ""),
            "关系类型": edge.get("relation_type", ""),
            "关联原因": edge.get("reason", ""),
        }
    if not isinstance(edge, (list, tuple)):
        return {"起点": "", "终点": "", "关系类型": "", "关联原因": ""}

    source = edge[0] if len(edge) >= 1 else ""
    target = edge[1] if len(edge) >= 2 else ""
    reason = edge[2] if len(edge) >= 3 else ""
    relation_type = edge[3] if len(edge) >= 4 else ""
    return {"起点": source, "终点": target, "关系类型": relation_type, "关联原因": reason}

def _decode_text_file(file_bytes):
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return file_bytes.decode(encoding), None
        except UnicodeDecodeError:
            continue
    return "", "文本文件编码无法识别，请使用 UTF-8、UTF-8 BOM 或 GB18030/GBK 编码。"

def _read_uploaded_text(uploaded_file):
    try:
        is_txt = uploaded_file.type == "text/plain" or uploaded_file.name.lower().endswith(".txt")
        if is_txt:
            return _decode_text_file(uploaded_file.read())

        is_pdf = uploaded_file.type == "application/pdf" or uploaded_file.name.lower().endswith(".pdf")
        if is_pdf:
            try:
                from pypdf import PdfReader
            except ImportError:
                return "", "缺少 PDF 解析依赖，请先安装 pypdf。"

            reader = PdfReader(uploaded_file)
            if reader.is_encrypted:
                try:
                    decrypt_result = reader.decrypt("")
                except Exception:
                    return "", "PDF 文件已加密，无法解析文本内容。"
                if not decrypt_result:
                    return "", "PDF 文件已加密，无法解析文本内容。"

            page_texts = []
            for page in reader.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    page_texts.append(page_text.strip())

            text = "\n\n".join(page_texts)
            if not text.strip():
                return "", "未能从 PDF 中提取文本。请确认 PDF 包含可复制的文本层，扫描版 PDF 暂不支持。"
            return text, None

        from docx import Document
        doc = Document(uploaded_file)
        text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        return text, None
    except Exception as e:
        return "", f"文件解析失败：{e}"

def _validate_prompt_templates(templates):
    errors = []
    required_placeholders = {
        "knowledge_extraction": ["{{text}}"],
        "graph_edges": ["{{name_list}}", "{{text}}"],
        "node_content": ["{{name}}", "{{definition}}"],
    }

    for key in DEFAULT_PROMPT_TEMPLATES:
        value = templates.get(key, "")
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{key} 不能为空")

    for key, placeholders in required_placeholders.items():
        template = templates.get(key, "")
        for placeholder in placeholders:
            if placeholder not in template:
                errors.append(f"{key} 缺少占位符 {placeholder}")

    return errors

def _render_prompt_template_page():
    st.markdown("### Prompt 模板配置")
    st.caption("模板保存到 prompt_templates.json。保存后回到课件生成页面，新的模型调用会使用更新后的模板。")

    templates = get_prompt_templates()

    with st.form("prompt_template_form"):
        system_prompt = st.text_area(
            "系统提示词：system_prompt",
            value=templates["system_prompt"],
            height=120,
        )
        knowledge_extraction = st.text_area(
            "知识点抽取模板：knowledge_extraction（占位符：{{text}}）",
            value=templates["knowledge_extraction"],
            height=240,
        )
        graph_edges = st.text_area(
            "知识关系抽取模板：graph_edges（占位符：{{name_list}}, {{text}}）",
            value=templates["graph_edges"],
            height=340,
        )
        node_content = st.text_area(
            "节点讲义模板：node_content（占位符：{{name}}, {{definition}}）",
            value=templates["node_content"],
            height=260,
        )

        col_save, col_reset = st.columns([1, 1])
        save_clicked = col_save.form_submit_button("保存模板", use_container_width=True)
        reset_clicked = col_reset.form_submit_button("恢复默认模板", use_container_width=True)

    if reset_clicked:
        save_prompt_templates(DEFAULT_PROMPT_TEMPLATES)
        st.success("已恢复默认模板。")
        st.rerun()

    if save_clicked:
        next_templates = {
            "system_prompt": system_prompt,
            "knowledge_extraction": knowledge_extraction,
            "graph_edges": graph_edges,
            "node_content": node_content,
        }
        errors = _validate_prompt_templates(next_templates)
        if errors:
            st.error("模板配置存在问题：\n" + "\n".join(errors))
        else:
            save_prompt_templates(next_templates)
            st.success("模板已保存到 prompt_templates.json。")

page = st.sidebar.radio("页面", ["课件生成", "Prompt 模板配置"])

if page == "Prompt 模板配置":
    _render_prompt_template_page()
    st.stop()

st.markdown("### 步骤 1：上传教学文档")
uploaded_file = st.file_uploader("上传教学文档（TXT、DOCX 或 PDF）", type=["txt", "docx", "pdf"])

if not uploaded_file:
    st.info("请上传教学文档以启动内容解析与课件生成流程。")
    st.stop()

if uploaded_file:
    raw_text, parse_error = _read_uploaded_text(uploaded_file)
    if parse_error:
        st.error(parse_error)
        st.stop()
    if not raw_text.strip():
        st.error("文件内容为空，请上传包含正文的 TXT、DOCX 或 PDF 文件。")
        st.stop()

    st.subheader("📖 文本预览")
    st.text_area("教学内容", raw_text, height=200)

    if st.button("🔍 解析并提取知识点"):
        with st.spinner("调用 DeepSeek 模型中..."):
            full_prompt = render_prompt_template("knowledge_extraction", text=raw_text)
            nodes = extract_knowledge(full_prompt)
            nodes, node_errors = _validate_nodes(nodes)
            if not nodes:
                st.error("未能成功提取知识点，请检查 Prompt 或内容格式。")
            else:
                if node_errors:
                    st.warning("部分知识点格式不完整，已自动跳过：\n" + "\n".join(node_errors))
                st.success("成功提取知识点，可在下方编辑")
                st.session_state["edited_nodes"] = nodes

    if "edited_nodes" in st.session_state:
        st.subheader("📋 当前知识点（可再次编辑）")
        st.session_state["edited_nodes"] = st.data_editor(
               st.session_state["edited_nodes"], key="node_editor_runtime"
           )
        st.markdown("---")
        st.subheader("📡 点击生成知识图谱")
        if st.button("🧠 生成知识图谱"):
            with st.spinner("生成图谱中..."):
                graph_nodes, node_errors = _validate_nodes(st.session_state["edited_nodes"])
                if node_errors:
                    st.error("请先修正知识点表格：\n" + "\n".join(node_errors))
                else:
                    edges = generate_graph_edges(raw_text, [n["name"] for n in graph_nodes])
                    st.session_state["edited_nodes"] = graph_nodes
                    st.session_state["graph_edges"] = edges
                    st.session_state["graph_nodes"] = graph_nodes

    if "graph_edges" in st.session_state:
         st.subheader(" 当前知识图谱（持续可见）")
         visualize_graph(st.session_state["graph_nodes"], st.session_state["graph_edges"])
         edge_rows = [_edge_to_row(edge) for edge in st.session_state["graph_edges"]]
         if edge_rows:
             st.subheader("🔗 知识点关联原因")
             st.dataframe(edge_rows, use_container_width=True, hide_index=True)

    if "edited_nodes" in st.session_state:
         st.markdown("---")
         st.subheader("📚 按需生成节点讲义内容")
         content_nodes, content_node_errors = _validate_nodes(st.session_state["edited_nodes"])
         if content_node_errors:
             st.warning("知识点表格存在待修正项，讲义生成将跳过无效行：\n" + "\n".join(content_node_errors))

         for node in content_nodes:
             if st.button(f"📄 为「{node['name']}」生成内容"):
                  result = generate_node_content(node["name"], node.get("definition", ""))
                  st.markdown(result)
