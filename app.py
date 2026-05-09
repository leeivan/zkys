# app.py
import streamlit as st
from deepseek_api import extract_knowledge, generate_graph_edges, generate_node_content
from graph_utils import visualize_graph

st.set_page_config(page_title="知识图谱自动生成演示平台", layout="wide")
st.title("📚 知识图谱自动生成演示平台")

def _edge_to_row(edge):
    if isinstance(edge, dict):
        return {
            "起点": edge.get("source", ""),
            "终点": edge.get("target", ""),
            "关联原因": edge.get("reason", ""),
        }
    if len(edge) >= 3:
        return {"起点": edge[0], "终点": edge[1], "关联原因": edge[2]}
    return {"起点": edge[0], "终点": edge[1], "关联原因": ""}

st.markdown("### 步骤 1：上传教学文档")
uploaded_file = st.file_uploader("上传教学文档（TXT 或 DOCX）", type=["txt", "docx"])

if not uploaded_file:
    st.info("请上传教学文档以启动内容解析与课件生成流程。")
    st.stop()

if uploaded_file:
    if uploaded_file.type == "text/plain":
        raw_text = uploaded_file.read().decode("utf-8")
    else:
        from docx import Document
        doc = Document(uploaded_file)
        raw_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])

    st.subheader("📖 文本预览")
    st.text_area("教学内容", raw_text, height=200)

    st.markdown("---")
    st.subheader("🔧 自定义知识点提取 Prompt")
    default_prompt = '''请从以下教学内容中提取 3~7 个核心知识点。每个知识点包含 name 和 definition 两个字段。
严格输出为 JSON 格式，例如：
[
  {"name": "术语A", "definition": "简要定义"},
  {"name": "术语B", "definition": "简要定义"}
]

教学内容如下：\n'''
    custom_prompt = st.text_area("Prompt 模板", value=default_prompt, height=200)

    if st.button("🔍 解析并提取知识点"):
        with st.spinner("调用 DeepSeek 模型中..."):
            full_prompt = f"{custom_prompt.strip()}\n\n{raw_text.strip()}"
            nodes = extract_knowledge(full_prompt)
            if not nodes:
                st.error("未能成功提取知识点，请检查 Prompt 或内容格式。")
            else:
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
                edges = generate_graph_edges(raw_text, [n["name"] for n in st.session_state["edited_nodes"]])
                st.session_state["graph_edges"] = edges  # 缓存边
                st.session_state["graph_nodes"] = st.session_state["edited_nodes"]  # 缓存节点

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
         content_template = st.text_area("节点内容模板（使用 {{name}}, {{definition}} 占位）", value="""
                ## {{name}}

                ### 定义
                {{definition}}

                ### 推导或背景知识
               （请补充详细公式或理论支撑）

                ### 应用场景或案例
               （请给出典型教学例子）

                ### 常见误区
               （列出1-2个典型误解）
             """, height=250)

         for node in st.session_state["edited_nodes"]:
             if st.button(f"📄 为「{node['name']}」生成内容"):
                  prompt = content_template.replace("{{name}}", node["name"]).replace("{{definition}}", node["definition"])
                  result = generate_node_content(prompt)
                  st.markdown(result)
