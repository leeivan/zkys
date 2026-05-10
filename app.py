import html

import streamlit as st
from deepseek_api import (
    extract_knowledge,
    generate_graph_edges,
    generate_node_content,
    get_last_error,
)
from graph_utils import visualize_graph
from prompt_config import (
    DEFAULT_PROMPT_TEMPLATES,
    render_text_prompt,
)
from user_store import (
    authenticate_user,
    change_user_password,
    create_auth_session,
    create_user,
    delete_auth_session,
    delete_user,
    get_auth_session_user,
    get_user_by_id,
    get_user_prompt_templates,
    has_admin_user,
    list_saved_graphs,
    list_users,
    save_knowledge_graph,
    save_user_prompt_templates,
    set_user_admin,
    set_user_password,
)

APP_NAME = "智课助教"
PAGE_WORKSPACE = "备课工作台"
PAGE_PROMPTS = "模板工坊"
PAGE_HISTORY = "教学档案"
PAGE_USERS = "账号管理"

st.set_page_config(page_title=f"{APP_NAME} · 教学辅助 APP", page_icon="📚", layout="wide")

GENERATION_STATE_KEYS = (
    "edited_nodes",
    "graph_nodes",
    "graph_edges",
    "node_editor_runtime",
    "source_key",
)
AUTH_STATE_KEY = "authenticated_user"
AUTH_TOKEN_STATE_KEY = "auth_session_token"
AUTH_TOKEN_QUERY_PARAM = "session"

def _escape_html(value):
    return html.escape("" if value is None else str(value), quote=True)

def _inject_app_style():
    st.markdown(
        """
        <style>
        :root {
            --app-bg: #f6f7f2;
            --app-surface: #ffffff;
            --app-surface-soft: #f9faf7;
            --app-ink: #17202a;
            --app-muted: #667085;
            --app-line: #dfe5df;
            --app-primary: #176b6b;
            --app-primary-dark: #0f4f52;
            --app-accent: #b56b28;
            --app-danger: #b42318;
            --app-shadow: 0 14px 38px rgba(28, 38, 47, 0.08);
        }

        .stApp {
            background:
                linear-gradient(180deg, rgba(246, 247, 242, 0.94), rgba(246, 247, 242, 1)),
                radial-gradient(circle at 12% 6%, rgba(23, 107, 107, 0.12), transparent 32%),
                radial-gradient(circle at 90% 16%, rgba(181, 107, 40, 0.13), transparent 28%);
            color: var(--app-ink);
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1280px;
        }

        section[data-testid="stSidebar"] {
            background: #102c33;
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }

        section[data-testid="stSidebar"] * {
            color: rgba(255, 255, 255, 0.92);
        }

        section[data-testid="stSidebar"] .stRadio label,
        section[data-testid="stSidebar"] .stCaptionContainer {
            color: rgba(255, 255, 255, 0.72);
        }

        .app-sidebar-brand {
            margin: 0.3rem 0 1.2rem;
            padding: 1rem 0.9rem;
            border: 1px solid rgba(255, 255, 255, 0.13);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.07);
        }

        .app-sidebar-brand strong {
            display: block;
            font-size: 1.25rem;
            line-height: 1.2;
            letter-spacing: 0;
        }

        .app-sidebar-brand span {
            display: block;
            margin-top: 0.35rem;
            color: rgba(255, 255, 255, 0.68);
            font-size: 0.82rem;
        }

        .app-hero {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            align-items: flex-end;
            margin-bottom: 1.1rem;
            padding: 1.1rem 1.25rem;
            border: 1px solid var(--app-line);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.86);
            box-shadow: var(--app-shadow);
        }

        .app-hero h1 {
            margin: 0;
            color: var(--app-ink);
            font-size: clamp(1.65rem, 2.2vw, 2.25rem);
            line-height: 1.2;
            letter-spacing: 0;
        }

        .app-hero p {
            margin: 0.35rem 0 0;
            color: var(--app-muted);
            font-size: 0.95rem;
            line-height: 1.55;
        }

        .app-badge {
            display: inline-flex;
            align-items: center;
            min-height: 2.2rem;
            padding: 0.35rem 0.7rem;
            border-radius: 999px;
            border: 1px solid rgba(23, 107, 107, 0.2);
            background: #eef7f4;
            color: var(--app-primary-dark);
            font-weight: 700;
            white-space: nowrap;
        }

        div[data-testid="stMetric"] {
            min-height: 78px;
            padding: 0.85rem 0.95rem;
            border: 1px solid var(--app-line);
            border-radius: 8px;
            background: var(--app-surface);
            box-shadow: 0 8px 24px rgba(28, 38, 47, 0.05);
        }

        div[data-testid="stMetricLabel"] {
            color: var(--app-muted);
            font-size: 0.82rem;
        }

        div[data-testid="stMetricValue"] {
            color: var(--app-primary-dark);
            font-size: 1.45rem;
            line-height: 1.15;
            letter-spacing: 0;
        }

        .section-title {
            margin: 1.15rem 0 0.6rem;
        }

        .section-title h2 {
            margin: 0;
            color: var(--app-ink);
            font-size: 1.18rem;
            line-height: 1.35;
            letter-spacing: 0;
        }

        .section-title p {
            margin: 0.25rem 0 0;
            color: var(--app-muted);
            font-size: 0.9rem;
            line-height: 1.45;
        }

        div[data-testid="stFileUploader"] {
            border: 1px dashed rgba(23, 107, 107, 0.35);
            border-radius: 8px;
            padding: 0.8rem;
            background: rgba(255, 255, 255, 0.72);
        }

        div[data-testid="stDataFrame"],
        div[data-testid="stDataEditor"] {
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid var(--app-line);
        }

        .stTextInput input,
        .stTextArea textarea,
        .stSelectbox div[data-baseweb="select"] > div {
            border-radius: 8px;
        }

        .stButton > button,
        .stFormSubmitButton > button {
            border-radius: 8px;
            border: 1px solid rgba(23, 107, 107, 0.34);
            background: var(--app-primary);
            color: #ffffff;
            font-weight: 700;
            min-height: 2.55rem;
            box-shadow: 0 8px 20px rgba(23, 107, 107, 0.16);
        }

        .stButton > button:hover,
        .stFormSubmitButton > button:hover {
            border-color: var(--app-primary-dark);
            background: var(--app-primary-dark);
            color: #ffffff;
        }

        .stButton > button:disabled,
        .stFormSubmitButton > button:disabled {
            background: #e5e7eb;
            color: #8a94a6;
            border-color: #d1d5db;
            box-shadow: none;
        }

        div[data-testid="stAlert"] {
            border-radius: 8px;
        }

        hr {
            margin: 1.4rem 0;
            border-color: var(--app-line);
        }

        @media (max-width: 900px) {
            .app-hero {
                display: block;
            }

            .app-badge {
                margin-top: 0.75rem;
            }

        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def _render_app_header(title, subtitle="", badge=""):
    subtitle_html = f"<p>{_escape_html(subtitle)}</p>" if subtitle else ""
    badge_html = f"<div class='app-badge'>{_escape_html(badge)}</div>" if badge else ""
    st.markdown(
        f"""
        <div class="app-hero">
          <div>
            <h1>{_escape_html(title)}</h1>
            {subtitle_html}
          </div>
          {badge_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

def _render_section_title(title, subtitle=""):
    subtitle_html = f"<p>{_escape_html(subtitle)}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div class="section-title">
          <h2>{_escape_html(title)}</h2>
          {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

def _render_metric_strip(metrics):
    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, metrics):
        col.metric(str(label), str(value))

def _render_sidebar_brand():
    st.sidebar.markdown(
        f"""
        <div class="app-sidebar-brand">
          <strong>{_escape_html(APP_NAME)}</strong>
          <span>教师备课工作台</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

_inject_app_style()

def _clear_generation_state():
    for key in GENERATION_STATE_KEYS:
        st.session_state.pop(key, None)

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
        try:
            uploaded_file.seek(0)
        except (AttributeError, OSError):
            pass

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

def _get_query_auth_token():
    token = st.query_params.get(AUTH_TOKEN_QUERY_PARAM, "")
    if isinstance(token, list):
        return token[0] if token else ""
    return token or ""

def _set_query_auth_token(token):
    if token:
        st.query_params[AUTH_TOKEN_QUERY_PARAM] = token

def _clear_query_auth_token():
    if AUTH_TOKEN_QUERY_PARAM in st.query_params:
        del st.query_params[AUTH_TOKEN_QUERY_PARAM]

def _set_current_user(user):
    previous_user_id = st.session_state.get("current_user_id")
    if previous_user_id and previous_user_id != user["id"]:
        _clear_generation_state()

    st.session_state[AUTH_STATE_KEY] = user
    st.session_state["current_user_id"] = user["id"]

def _persist_current_user(user):
    token = create_auth_session(user["id"])
    st.session_state[AUTH_TOKEN_STATE_KEY] = token
    _set_query_auth_token(token)

def _restore_current_user_from_token():
    token = st.session_state.get(AUTH_TOKEN_STATE_KEY) or _get_query_auth_token()
    if not token:
        return None

    user = get_auth_session_user(token)
    if not user:
        st.session_state.pop(AUTH_TOKEN_STATE_KEY, None)
        _clear_query_auth_token()
        return None

    st.session_state[AUTH_TOKEN_STATE_KEY] = token
    _set_current_user(user)
    return user

def _refresh_current_user():
    current_user_id = st.session_state.get("current_user_id")
    if not current_user_id:
        return

    user = get_user_by_id(current_user_id)
    if user:
        st.session_state[AUTH_STATE_KEY] = user
    else:
        _logout_current_user()

def _logout_current_user():
    token = st.session_state.get(AUTH_TOKEN_STATE_KEY) or _get_query_auth_token()
    if token:
        delete_auth_session(token)
    _clear_generation_state()
    st.session_state.pop(AUTH_STATE_KEY, None)
    st.session_state.pop(AUTH_TOKEN_STATE_KEY, None)
    st.session_state.pop("current_user_id", None)
    _clear_query_auth_token()

def _render_auth_page():
    _render_app_header(APP_NAME, "面向教师的备课与课堂材料工作台", "账号登录")
    login_tab, register_tab = st.tabs(["登录", "注册"])

    with login_tab:
        with st.form("login_form"):
            username = st.text_input("用户名", key="login_username")
            password = st.text_input("密码", type="password", key="login_password")
            login_clicked = st.form_submit_button("登录", width="stretch")

        if login_clicked:
            user = authenticate_user(username, password)
            if user:
                _set_current_user(user)
                _persist_current_user(user)
                st.success("登录成功。")
                st.rerun()
            else:
                st.error("用户名或密码错误。未设置密码的旧用户可以到“注册”页用同名账号设置密码。")

    with register_tab:
        with st.form("register_form"):
            new_username = st.text_input("用户名", key="register_username")
            new_password = st.text_input("密码", type="password", key="register_password")
            confirm_password = st.text_input("确认密码", type="password", key="register_confirm_password")
            register_clicked = st.form_submit_button("注册并登录", width="stretch")

        if register_clicked:
            if new_password != confirm_password:
                st.error("两次输入的密码不一致。")
            else:
                try:
                    user = create_user(new_username, new_password)
                except ValueError as error:
                    st.error(str(error))
                else:
                    _set_current_user(user)
                    _persist_current_user(user)
                    role_message = "，你已成为管理员" if user.get("is_admin") else ""
                    st.success(f"注册成功，已自动登录{role_message}。")
                    st.rerun()

    st.info("用户数据保存在本地 data/users 目录中。系统没有管理员时，首个注册或补密码的用户会自动成为管理员。")

def _select_current_user():
    _render_sidebar_brand()
    st.sidebar.markdown("### 当前账号")
    current_user = st.session_state.get(AUTH_STATE_KEY)
    if not current_user:
        current_user = _restore_current_user_from_token()

    if current_user and current_user.get("id"):
        refreshed_user = get_user_by_id(current_user["id"])
        if not refreshed_user:
            _logout_current_user()
            st.rerun()
        if not has_admin_user():
            refreshed_user = set_user_admin(refreshed_user["id"], True)
        st.session_state[AUTH_STATE_KEY] = refreshed_user
        current_user = refreshed_user
        if not st.session_state.get(AUTH_TOKEN_STATE_KEY) and not _get_query_auth_token():
            _persist_current_user(current_user)

        role = "管理员" if current_user.get("is_admin") else "普通用户"
        st.sidebar.caption(f"当前用户：{current_user['username']}（{role}）")
        if st.sidebar.button("退出登录", width="stretch"):
            _logout_current_user()
            st.rerun()
        return current_user

    st.sidebar.info("请先登录或注册")
    _render_auth_page()
    st.stop()

def _render_prompt_template_page(user):
    _render_app_header(PAGE_PROMPTS, "调整教学内容生成口径", f"{user['username']}")

    templates = get_user_prompt_templates(user["id"])

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
        save_clicked = col_save.form_submit_button("保存模板", width="stretch")
        reset_clicked = col_reset.form_submit_button("恢复默认模板", width="stretch")

    if reset_clicked:
        save_user_prompt_templates(user["id"], DEFAULT_PROMPT_TEMPLATES)
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
            save_user_prompt_templates(user["id"], next_templates)
            st.success("模板已保存到当前用户配置。")

def _render_history_page(user):
    _render_app_header(PAGE_HISTORY, "保存过的知识结构与讲义素材", f"{user['username']}")

    records = list_saved_graphs(user["id"])
    if not records:
        st.info("当前用户还没有保存过知识图谱。")
        return

    labels = [
        f"{record.get('created_at', '')} · {record.get('title', '未命名知识图谱')}"
        for record in records
    ]
    selected_index = st.selectbox("选择历史记录", range(len(records)), format_func=lambda index: labels[index])
    record = records[selected_index]
    nodes = record.get("nodes", [])
    edges = record.get("edges", [])

    st.markdown(f"**标题：** {record.get('title', '未命名知识图谱')}")
    st.markdown(f"**来源文件：** {record.get('source_filename', '未知')}")
    st.markdown(f"**保存时间：** {record.get('created_at', '')}")

    if record.get("source_excerpt"):
        with st.expander("查看原文摘录"):
            st.text(record["source_excerpt"])

    st.subheader("知识点")
    st.dataframe(nodes, width="stretch", hide_index=True)

    st.subheader("知识图谱")
    visualize_graph(nodes, edges)

    edge_rows = [_edge_to_row(edge) for edge in edges]
    if edge_rows:
        st.subheader("知识点关联原因")
        st.dataframe(edge_rows, width="stretch", hide_index=True)

    if st.button(f"载入到{PAGE_WORKSPACE}"):
        st.session_state["edited_nodes"] = nodes
        st.session_state["graph_nodes"] = nodes
        st.session_state["graph_edges"] = edges
        st.success(f"已载入到当前会话。切换到“{PAGE_WORKSPACE}”页面即可继续查看或生成讲义。")

def _render_user_management_page(user):
    role = "管理员" if user.get("is_admin") else "普通用户"
    _render_app_header(PAGE_USERS, "账号、密码与权限", f"{user['username']} · {role}")

    _render_section_title("账户设置")
    with st.form("change_password_form"):
        current_password = st.text_input("当前密码", type="password")
        new_password = st.text_input("新密码", type="password")
        confirm_password = st.text_input("确认新密码", type="password")
        change_clicked = st.form_submit_button("保存新密码", width="stretch")

    if change_clicked:
        if new_password != confirm_password:
            st.error("两次输入的新密码不一致。")
        else:
            try:
                updated_user = change_user_password(user["id"], current_password, new_password)
            except ValueError as error:
                st.error(str(error))
            else:
                _set_current_user(updated_user)
                st.success("密码已更新。")

    if not user.get("is_admin"):
        st.info("只有管理员可以查看和管理其他注册用户。")
        return

    _render_section_title("管理员后台")
    users = list_users()
    user_rows = [
        {
            "用户名": item.get("username", ""),
            "权限": "管理员" if item.get("is_admin") else "普通用户",
            "创建时间": item.get("created_at", ""),
            "最近登录/更新": item.get("updated_at", ""),
            "已设置密码": "是" if item.get("has_password") else "否",
        }
        for item in users
    ]
    if user_rows:
        st.dataframe(user_rows, width="stretch", hide_index=True)
    else:
        st.info("暂无本地用户。")
        return

    selected_index = st.selectbox(
        "选择要管理的用户",
        range(len(users)),
        format_func=lambda index: f"{users[index].get('username', '')}（{'管理员' if users[index].get('is_admin') else '普通用户'}）",
    )
    target_user = users[selected_index]
    target_is_self = target_user.get("id") == user.get("id")

    st.markdown(f"**当前选择：** {target_user.get('username', '')}")

    with st.form("admin_reset_password_form"):
        reset_password = st.text_input("重置为新密码", type="password", key="admin_reset_password")
        reset_confirm = st.text_input("确认新密码", type="password", key="admin_reset_confirm")
        reset_clicked = st.form_submit_button(
            "重置该用户密码",
            width="stretch",
            disabled=target_is_self,
        )

    if target_is_self:
        st.caption("当前账号请使用上方“账户设置”修改密码。")

    if reset_clicked:
        if reset_password != reset_confirm:
            st.error("两次输入的新密码不一致。")
        else:
            try:
                set_user_password(target_user["id"], reset_password)
            except ValueError as error:
                st.error(str(error))
            else:
                st.success("用户密码已重置。")
                st.rerun()

    role_button_label = "取消管理员权限" if target_user.get("is_admin") else "设为管理员"
    role_button_disabled = target_is_self
    if st.button(role_button_label, width="stretch", disabled=role_button_disabled):
        try:
            set_user_admin(target_user["id"], not target_user.get("is_admin"))
        except ValueError as error:
            st.error(str(error))
        else:
            st.success("用户权限已更新。")
            st.rerun()

    if target_is_self:
        st.caption("不能在当前会话中修改自己的管理员权限或删除自己。")

    with st.form("admin_delete_user_form"):
        delete_confirm = st.text_input(
            f"输入用户名 {target_user.get('username', '')} 确认删除",
            key="admin_delete_confirm",
        )
        delete_clicked = st.form_submit_button(
            "删除该用户及其数据",
            width="stretch",
            disabled=target_is_self,
        )

    if delete_clicked:
        if delete_confirm != target_user.get("username"):
            st.error("确认用户名不匹配，未删除用户。")
        else:
            try:
                delete_user(target_user["id"])
            except ValueError as error:
                st.error(str(error))
            else:
                st.success("用户及其本地数据已删除。")
                st.rerun()

def _render_graph_result(user, raw_text="", source_filename=""):
    _render_section_title("知识图谱", "概念关系与节点结构")
    visualize_graph(st.session_state["graph_nodes"], st.session_state["graph_edges"])
    edge_rows = [_edge_to_row(edge) for edge in st.session_state["graph_edges"]]
    if edge_rows:
        _render_section_title("关联说明")
        st.dataframe(edge_rows, width="stretch", hide_index=True)

    if raw_text and source_filename:
        save_title = st.text_input("保存标题", value=f"{source_filename} 知识图谱")
        if st.button("保存本次知识点和知识图谱"):
            record = save_knowledge_graph(
                user["id"],
                save_title,
                source_filename,
                st.session_state["graph_nodes"],
                st.session_state["graph_edges"],
                raw_text,
            )
            st.success(f"已保存：{record['title']}")

def _render_node_content_tools(user):
    if "edited_nodes" not in st.session_state:
        return

    st.markdown("---")
    _render_section_title("讲义生成", "按知识点生成可编辑材料")
    content_nodes, content_node_errors = _validate_nodes(st.session_state["edited_nodes"])
    if content_node_errors:
        st.warning("知识点表格存在待修正项，讲义生成将跳过无效行：\n" + "\n".join(content_node_errors))

    for node in content_nodes:
        if st.button(f"为「{node['name']}」生成内容"):
            user_templates = get_user_prompt_templates(user["id"])
            result = generate_node_content(
                node["name"],
                node.get("definition", ""),
                template=user_templates["node_content"],
                system_prompt=user_templates["system_prompt"],
            )
            if result:
                st.markdown(result)
            else:
                st.error(get_last_error() or "未能生成讲义内容，请检查 API 配置或稍后重试。")

def _render_workspace_page(current_user):
    role = "管理员" if current_user.get("is_admin") else "教师"
    saved_count = len(list_saved_graphs(current_user["id"]))
    edited_count = len(_as_records(st.session_state.get("edited_nodes", [])))
    edge_count = len(st.session_state.get("graph_edges", []))

    _render_app_header(PAGE_WORKSPACE, "教学材料、知识图谱与讲义生成", f"{current_user['username']} · {role}")
    _render_metric_strip(
        [
            ("教学档案", saved_count),
            ("当前知识点", edited_count),
            ("知识关系", edge_count),
            ("当前身份", role),
        ]
    )

    _render_section_title("教学材料")
    upload_col, preview_col = st.columns([0.36, 0.64], gap="large")
    raw_text = ""
    uploaded_file = None

    with upload_col:
        uploaded_file = st.file_uploader("上传教学文档", type=["txt", "docx", "pdf"])

    if not uploaded_file:
        with preview_col:
            if "graph_edges" in st.session_state and "graph_nodes" in st.session_state:
                st.info("已载入教学档案，可继续查看图谱或生成讲义。")
            else:
                st.info("请选择 TXT、DOCX 或 PDF 文档。")

        if "graph_edges" in st.session_state and "graph_nodes" in st.session_state:
            _render_graph_result(current_user)
            _render_node_content_tools(current_user)
        return

    source_key = f"{current_user['id']}:{uploaded_file.name}:{getattr(uploaded_file, 'size', 0)}"
    if st.session_state.get("source_key") != source_key:
        _clear_generation_state()
        st.session_state["source_key"] = source_key

    raw_text, parse_error = _read_uploaded_text(uploaded_file)
    if parse_error:
        with preview_col:
            st.error(parse_error)
        return
    if not raw_text.strip():
        with preview_col:
            st.error("文件内容为空，请上传包含正文的 TXT、DOCX 或 PDF 文件。")
        return

    with preview_col:
        st.text_area("教学内容", raw_text, height=260)

    _render_section_title("知识点加工")
    action_col, editor_col = st.columns([0.3, 0.7], gap="large")

    with action_col:
        if st.button("提取知识点", width="stretch"):
            with st.spinner("调用 DeepSeek 模型中..."):
                user_templates = get_user_prompt_templates(current_user["id"])
                full_prompt = render_text_prompt(user_templates["knowledge_extraction"], raw_text)
                nodes = extract_knowledge(full_prompt, system_prompt=user_templates["system_prompt"])
                nodes, node_errors = _validate_nodes(nodes)
                if not nodes:
                    error_detail = get_last_error()
                    if error_detail:
                        st.error(f"未能成功提取知识点：{error_detail}")
                    else:
                        st.error("未能成功提取知识点，请检查 Prompt 或内容格式。")
                else:
                    if node_errors:
                        st.warning("部分知识点格式不完整，已自动跳过：\n" + "\n".join(node_errors))
                    st.session_state["edited_nodes"] = nodes
                    st.success("知识点已生成。")

        graph_ready = "edited_nodes" in st.session_state
        if st.button("生成知识图谱", width="stretch", disabled=not graph_ready):
            with st.spinner("生成图谱中..."):
                graph_nodes, node_errors = _validate_nodes(st.session_state["edited_nodes"])
                if node_errors:
                    st.error("请先修正知识点表格：\n" + "\n".join(node_errors))
                else:
                    user_templates = get_user_prompt_templates(current_user["id"])
                    edges = generate_graph_edges(
                        raw_text,
                        [n["name"] for n in graph_nodes],
                        graph_edges_template=user_templates["graph_edges"],
                        system_prompt=user_templates["system_prompt"],
                    )
                    if not edges:
                        error_detail = get_last_error()
                        if error_detail:
                            st.warning(f"未能生成知识关系：{error_detail}")
                        else:
                            st.warning("未生成知识关系，可先保存知识点，或调整 Prompt 后重新生成。")
                    st.session_state["edited_nodes"] = graph_nodes
                    st.session_state["graph_edges"] = edges
                    st.session_state["graph_nodes"] = graph_nodes

    with editor_col:
        if "edited_nodes" in st.session_state:
            st.session_state["edited_nodes"] = st.data_editor(
                st.session_state["edited_nodes"],
                key="node_editor_runtime",
                width="stretch",
                num_rows="dynamic",
                column_config={
                    "name": st.column_config.TextColumn("知识点", required=True),
                    "definition": st.column_config.TextColumn("定义"),
                },
            )
        else:
            st.info("知识点将在这里显示。")

    if "graph_edges" in st.session_state:
        _render_graph_result(current_user, raw_text, uploaded_file.name)

    if "edited_nodes" in st.session_state:
        _render_node_content_tools(current_user)

current_user = _select_current_user()
page = st.sidebar.radio("工作区", [PAGE_WORKSPACE, PAGE_PROMPTS, PAGE_HISTORY, PAGE_USERS])

if page == PAGE_PROMPTS:
    _render_prompt_template_page(current_user)
    st.stop()

if page == PAGE_HISTORY:
    _render_history_page(current_user)
    st.stop()

if page == PAGE_USERS:
    _render_user_management_page(current_user)
    st.stop()

_render_workspace_page(current_user)
