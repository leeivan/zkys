# graph_utils.py
import streamlit.components.v1 as components
import json

def _text_width(text):
    return sum(2 if ord(char) > 127 else 1 for char in text)

def _node_dimensions(label):
    width = min(max(104, _text_width(label) * 8 + 36), 220)
    height = 48 if width < 160 else 62
    return width, height

def _edge_fields(edge):
    if isinstance(edge, dict):
        source = edge.get("source") or edge.get("from") or edge.get("src") or ""
        target = edge.get("target") or edge.get("to") or edge.get("dst") or ""
        reason = edge.get("reason") or edge.get("label") or edge.get("relation") or ""
        return str(source).strip(), str(target).strip(), str(reason).strip()

    if len(edge) >= 3:
        return str(edge[0]).strip(), str(edge[1]).strip(), str(edge[2]).strip()

    return str(edge[0]).strip(), str(edge[1]).strip(), ""

def _short_reason(reason):
    if not reason:
        return "关联原因"
    return reason if len(reason) <= 18 else f"{reason[:17]}..."

def visualize_graph(nodes, edges):
    print("📌 DEBUG: 节点 =", nodes)
    print("📌 DEBUG: 边 =", edges)

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
        src, dst, reason = _edge_fields(edge)
        edge_key = (src, dst)
        if src in node_ids and dst in node_ids and edge_key not in seen_edges:
            seen_edges.add(edge_key)
            unique_edges.append({
                "source": src,
                "target": dst,
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
                "reason": edge["reason"],
                "shortReason": _short_reason(edge["reason"]),
                "relationTitle": f"{edge['source']} → {edge['target']}",
            }
        })

    elements_json = json.dumps(elements, ensure_ascii=False).replace("</", "<\\/")
    print("📌 DEBUG: 可视化元素 =", elements_json[:300], "...")

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset='utf-8'>
      <script src='https://unpkg.com/cytoscape@3.23.0/dist/cytoscape.min.js'></script>
      <style>
        html, body {{
          margin: 0;
          padding: 0;
          width: 100%;
          height: 100%;
          overflow: hidden;
          font-family: "Microsoft YaHei", "PingFang SC", Arial, sans-serif;
          color: #17233c;
        }}

        .graph-shell {{
          position: relative;
          width: 100%;
          height: 700px;
          overflow: hidden;
          border: 1px solid #d9e2ef;
          border-radius: 8px;
          background:
            radial-gradient(circle at 20px 20px, rgba(63, 99, 150, 0.08) 1px, transparent 1px),
            linear-gradient(135deg, #f8fbff 0%, #eef4f9 52%, #f8faf4 100%);
          background-size: 28px 28px, 100% 100%;
        }}

        #cy {{
          width: 100%;
          height: 100%;
        }}

        .toolbar {{
          position: absolute;
          z-index: 2;
          top: 14px;
          left: 14px;
          display: flex;
          gap: 8px;
          align-items: center;
          padding: 8px;
          border: 1px solid rgba(132, 149, 173, 0.22);
          border-radius: 8px;
          background: rgba(255, 255, 255, 0.88);
          box-shadow: 0 12px 34px rgba(54, 73, 99, 0.12);
          backdrop-filter: blur(10px);
        }}

        .toolbar button {{
          height: 32px;
          border: 1px solid #cad6e4;
          border-radius: 6px;
          background: #ffffff;
          color: #24324a;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          padding: 0 12px;
          transition: all 0.18s ease;
        }}

        .toolbar button:hover {{
          border-color: #5f8fd6;
          color: #1f5da8;
          box-shadow: 0 4px 12px rgba(67, 120, 211, 0.16);
        }}

        .detail-panel {{
          position: absolute;
          z-index: 2;
          top: 74px;
          right: 14px;
          width: min(340px, calc(100% - 28px));
          max-height: 560px;
          box-sizing: border-box;
          overflow: auto;
          padding: 16px;
          border: 1px solid rgba(132, 149, 173, 0.22);
          border-radius: 8px;
          background: rgba(255, 255, 255, 0.9);
          box-shadow: 0 18px 44px rgba(54, 73, 99, 0.14);
          backdrop-filter: blur(10px);
        }}

        .panel-kicker {{
          margin-bottom: 6px;
          color: #667389;
          font-size: 12px;
          font-weight: 700;
        }}

        .detail-panel h3 {{
          margin: 0 0 10px;
          font-size: 18px;
          line-height: 1.35;
          letter-spacing: 0;
        }}

        .detail-panel p {{
          margin: 0;
          color: #43506a;
          font-size: 13px;
          line-height: 1.65;
          white-space: pre-wrap;
        }}

        .metrics {{
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
          margin-top: 14px;
        }}

        .metric {{
          padding: 10px;
          border: 1px solid #e4ebf3;
          border-radius: 8px;
          background: #f7fafc;
        }}

        .metric strong {{
          display: block;
          color: #1f5da8;
          font-size: 20px;
          line-height: 1.1;
        }}

        .metric span {{
          color: #667389;
          font-size: 12px;
        }}

        .relation-path {{
          display: inline-block;
          margin-bottom: 10px;
          padding: 7px 9px;
          border-radius: 8px;
          background: #eef6ff;
          color: #1d5fa7;
          font-size: 13px;
          font-weight: 700;
          line-height: 1.35;
        }}

        .statusbar {{
          position: absolute;
          z-index: 2;
          left: 14px;
          bottom: 14px;
          padding: 8px 11px;
          border: 1px solid rgba(132, 149, 173, 0.22);
          border-radius: 8px;
          background: rgba(255, 255, 255, 0.86);
          color: #536179;
          font-size: 12px;
          box-shadow: 0 10px 28px rgba(54, 73, 99, 0.12);
          backdrop-filter: blur(10px);
        }}

        @media (max-width: 720px) {{
          .graph-shell {{
            height: 640px;
          }}

          .toolbar {{
            right: 14px;
            flex-wrap: wrap;
          }}

          .detail-panel {{
            top: auto;
            bottom: 52px;
            left: 14px;
            right: 14px;
            width: auto;
            max-height: 220px;
          }}
        }}
      </style>
    </head>
    <body>
      <div class='graph-shell'>
        <div class='toolbar'>
          <button id='fit-btn'>适配</button>
          <button id='layout-btn'>重排</button>
          <button id='expand-btn'>展开</button>
          <button id='collapse-btn'>收起下游</button>
        </div>
        <div id='cy'></div>
        <aside class='detail-panel'>
          <div class='panel-kicker' id='panel-kicker'>图谱概览</div>
          <h3 id='node-title'>知识图谱</h3>
          <div id='relation-path' class='relation-path' style='display: none;'></div>
          <p id='node-definition'>共 {len(nodes)} 个知识点，{len(unique_edges)} 条关系。点击关系线可查看两个知识点关联的原因。</p>
          <div class='metrics' id='node-metrics'>
            <div class='metric'><strong id='node-in'>0</strong><span>上游关系</span></div>
            <div class='metric'><strong id='node-out'>0</strong><span>下游关系</span></div>
          </div>
        </aside>
        <div class='statusbar'>{len(nodes)} 个知识点 · {len(unique_edges)} 条关系</div>
      </div>
      <script>
        const graphElements = {elements_json};
        let selectedNode = null;

        var cy = cytoscape({{
          container: document.getElementById('cy'),
          elements: graphElements,
          minZoom: 0.35,
          maxZoom: 2.2,
          wheelSensitivity: 0.24,
          style: [
            {{
              selector: 'node',
              style: {{
                'shape': 'roundrectangle',
                'width': 'data(width)',
                'height': 'data(height)',
                'background-color': '#ffffff',
                'border-color': '#4f82c8',
                'border-width': 2,
                'label': 'data(label)',
                'color': '#18243b',
                'font-size': 13,
                'font-weight': 600,
                'font-family': '"Microsoft YaHei", "PingFang SC", Arial, sans-serif',
                'text-wrap': 'wrap',
                'text-max-width': 'data(textMaxWidth)',
                'text-valign': 'center',
                'text-halign': 'center',
                'overlay-opacity': 0,
                'transition-property': 'background-color, border-color, opacity, width, height',
                'transition-duration': '180ms'
              }}
            }},
            {{ selector: 'node.root', style: {{ 'background-color': '#eaf8f3', 'border-color': '#2f9e7e' }} }},
            {{ selector: 'node.leaf', style: {{ 'background-color': '#fff6e3', 'border-color': '#d89520' }} }},
            {{ selector: 'node.hub', style: {{ 'background-color': '#f1ecff', 'border-color': '#7c62d6' }} }},
            {{ selector: 'node.isolated', style: {{ 'background-color': '#f1f5f9', 'border-color': '#94a3b8' }} }},
            {{
              selector: 'edge',
              style: {{
                'width': 2.4,
                'curve-style': 'bezier',
                'line-color': '#9aa8b8',
                'target-arrow-shape': 'triangle',
                'target-arrow-color': '#9aa8b8',
                'arrow-scale': 1.15,
                'label': 'data(shortReason)',
                'color': '#475569',
                'font-size': 10,
                'font-weight': 600,
                'text-background-color': '#ffffff',
                'text-background-opacity': 0.88,
                'text-background-padding': 4,
                'text-background-shape': 'roundrectangle',
                'text-rotation': 'autorotate',
                'text-margin-y': -8,
                'opacity': 0.86,
                'transition-property': 'line-color, target-arrow-color, opacity, width',
                'transition-duration': '180ms'
              }}
            }},
            {{
              selector: '.dim',
              style: {{ 'opacity': 0.18 }}
            }},
            {{
              selector: 'edge.highlighted',
              style: {{
                'width': 3.6,
                'line-color': '#316dcc',
                'target-arrow-color': '#316dcc',
                'color': '#164f91',
                'opacity': 1
              }}
            }},
            {{
              selector: 'edge.selected-edge',
              style: {{
                'width': 4.2,
                'line-color': '#0f5fa8',
                'target-arrow-color': '#0f5fa8',
                'color': '#0f5fa8',
                'opacity': 1
              }}
            }},
            {{
              selector: 'node.highlighted',
              style: {{
                'border-width': 3,
                'border-color': '#316dcc',
                'background-color': '#eef6ff',
                'opacity': 1
              }}
            }},
            {{
              selector: 'node.selected-node',
              style: {{
                'border-width': 4,
                'border-color': '#0f5fa8',
                'background-color': '#e7f2ff'
              }}
            }}
          ],
          layout: {{
            name: 'breadthfirst',
            directed: true,
            spacingFactor: 1.35,
            padding: 64,
            avoidOverlap: true,
            animate: false
          }}
        }});

        function setOverviewPanel() {{
          document.getElementById('panel-kicker').textContent = '图谱概览';
          document.getElementById('node-title').textContent = '知识图谱';
          document.getElementById('relation-path').style.display = 'none';
          document.getElementById('node-definition').textContent = '共 {len(nodes)} 个知识点，{len(unique_edges)} 条关系。点击关系线可查看两个知识点关联的原因。';
          document.getElementById('node-metrics').style.display = 'grid';
          document.getElementById('node-in').textContent = '0';
          document.getElementById('node-out').textContent = '0';
        }}

        function setNodePanel(node) {{
          const title = document.getElementById('node-title');
          const definition = document.getElementById('node-definition');
          const inDegree = document.getElementById('node-in');
          const outDegree = document.getElementById('node-out');

          if (!node) {{
            setOverviewPanel();
            return;
          }}

          document.getElementById('panel-kicker').textContent = '知识点';
          document.getElementById('relation-path').style.display = 'none';
          document.getElementById('node-metrics').style.display = 'grid';
          title.textContent = node.data('label');
          definition.textContent = node.data('definition') || '暂无定义';
          inDegree.textContent = node.data('inDegree') || 0;
          outDegree.textContent = node.data('outDegree') || 0;
        }}

        function setEdgePanel(edge) {{
          document.getElementById('panel-kicker').textContent = '关联原因';
          document.getElementById('node-title').textContent = '为什么相连';
          const relationPath = document.getElementById('relation-path');
          relationPath.textContent = edge.data('relationTitle');
          relationPath.style.display = 'inline-block';
          document.getElementById('node-definition').textContent = edge.data('reason') || '二者在教学内容中存在直接知识联系';
          document.getElementById('node-metrics').style.display = 'none';
        }}

        function clearFocus() {{
          cy.elements().removeClass('dim highlighted selected-node selected-edge');
          selectedNode = null;
          setOverviewPanel();
        }}

        function focusNode(node) {{
          selectedNode = node;
          cy.elements().removeClass('dim highlighted selected-node selected-edge');
          const neighborhood = node.closedNeighborhood();
          cy.elements().difference(neighborhood).addClass('dim');
          neighborhood.addClass('highlighted');
          node.addClass('selected-node');
          setNodePanel(node);
        }}

        function focusEdge(edge) {{
          selectedNode = null;
          cy.elements().removeClass('dim highlighted selected-node selected-edge');
          const endpoints = edge.connectedNodes();
          cy.elements().difference(edge.union(endpoints)).addClass('dim');
          endpoints.addClass('highlighted');
          edge.addClass('highlighted selected-edge');
          setEdgePanel(edge);
        }}

        function runLayout() {{
          cy.elements().show();
          cy.layout({{
            name: 'breadthfirst',
            directed: true,
            spacingFactor: 1.35,
            padding: 64,
            avoidOverlap: true,
            animate: true,
            animationDuration: 420
          }}).run();
          setTimeout(function() {{
            cy.fit(cy.elements(':visible'), 54);
          }}, 460);
          clearFocus();
        }}

        cy.on('tap', 'node', function(evt) {{
          focusNode(evt.target);
        }});

        cy.on('tap', 'edge', function(evt) {{
          focusEdge(evt.target);
        }});

        cy.on('tap', function(evt) {{
          if (evt.target === cy) {{
            clearFocus();
          }}
        }});

        document.getElementById('fit-btn').addEventListener('click', function() {{
          cy.fit(cy.elements(':visible'), 54);
        }});

        document.getElementById('layout-btn').addEventListener('click', runLayout);

        document.getElementById('expand-btn').addEventListener('click', function() {{
          cy.elements().show();
          cy.fit(cy.elements(':visible'), 54);
        }});

        document.getElementById('collapse-btn').addEventListener('click', function() {{
          if (!selectedNode) {{
            return;
          }}
          const downstream = selectedNode.successors();
          const visibleDownstream = downstream.nodes().filter(':visible');
          if (visibleDownstream.length > 0) {{
            downstream.hide();
          }} else {{
            downstream.show();
          }}
          selectedNode.show();
          focusNode(selectedNode);
          cy.fit(cy.elements(':visible'), 54);
        }});

        cy.ready(function() {{
          cy.fit(cy.elements(':visible'), 54);
        }});
      </script>
    </body>
    </html>
    """

    components.html(html_content, height=720, scrolling=False)
