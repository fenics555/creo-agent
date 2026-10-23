<!DOCTYPE html>
<html lang='en'>
<head>
    <meta charset='UTF-8'>
    <title>PLM Dependency Graph</title>
    <script type='text/javascript' src='https://unpkg.com/vis-network/standalone/umd/vis-network.min.js'></script>
    <style type='text/css'>
        body, html { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; font-family: sans-serif; background-color: #1e1e1e; }
        #network { width: 100%; height: 100%; }
        #info { position: absolute; top: 15px; left: 15px; background: rgba(255,255,255,0.9); padding: 15px; border-radius: 8px; z-index: 10; box-shadow: 0 2px 10px rgba(0,0,0,0.3); min-width: 250px; }
        h3 { margin: 0 0 10px 0; font-size: 16px; color: #222; border-bottom: 1px solid #ccc; padding-bottom: 5px; }
        .legend { font-size: 12px; margin-top: 10px; }
        .legend-item { display: flex; align-items: center; margin-bottom: 4px; }
        .color-box { width: 12px; height: 12px; margin-right: 8px; border-radius: 2px; }
        #node-info { font-size: 13px; color: #444; margin-top: 10px; }
    </style>
</head>
<body>
    <div id='info'>
        <h3 style='color:#222'>PLM Dependency Graph</h3>
        <div class='legend'>
            <div class='legend-item'><div class='color-box' style='background: #2B7CE9;'></div> <b style='color:#222'>BOM Flow (↓)</b> [Assembly &rarr; Part]</div>
            <div class='legend-item'><div class='color-box' style='background: #D62728;'></div> <b style='color:#222'>Genealogy (↑)</b> [Part &rarr; Master]</div>
        </div>
        <div id='node-info' style='color:#444'>Hover over a node to see details</div>
    </div>
    <div id='network'></div>
    <script type='text/javascript'>
        var nodes = new vis.DataSet(

''');
        var edges = new vis.DataSet(

''');
        var container = document.getElementById('network');
        var data = { nodes: nodes, edges: edges };
        var options = {
            nodes: { shape: 'dot', size: 25, font: { size: 14, color: '#ffffff' }, borderWidth: 2, shadow: true },
            edges: { arrows: { to: { enabled: true, scaleFactor: 1 } }, font: { align: 'middle', size: 10, color: '#aaa' }, smooth: { type: 'cubicBezier', forceDirection: 'none', roundness: 0.5 } },
            physics: { forceAtlas2Based: { gravitationalConstant: -100, centralGravity: 0.01, springLength: 150, springConstant: 0.08 }, maxVelocity: 50, solver: 'forceAtlas2Based', stabilization: { iterations: 200 } },
            interaction: { hover: true, multiselect: true }
        };
        var network = new vis.Network(container, data, options);
        network.on("hoverNode", function (params) {
            var nodeId = params.node;
            var nodeData = nodes.get(nodeId);
            document.getElementById('node-info').innerHTML = "<strong style='color:#222'>Name:</strong> " + nodeData.label + "<br><strong style='color:#222'>Type:</strong> " + (nodeData.plm_type || 'N/A');
        });
    </script>
</body>
</html>

def generate_html_file(nodes_list, edges_list, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(chunks[0])
        f.write(json.dumps(nodes_list, ensure_ascii=False))
        f.write(chunks[1])
        f.write(json.dumps(edges_list, ensure_ascii=False))
        f.write(chunks[2])
        f.write(chunks[3])
    print(f"[+] Created: {output_path}")

def run():
    JSON_PATH = r'D:\AI\tools\agent\creo_reverse_engineering\output\master_plm_graph.json'
    HTML_OUTPUT_FULL = r'D:\AI\tools\agent\creo_reverse_engineering\output\graph_full.html'
    HTML_OUTPUT_TOP = r'D:\AI\tools\agent\creo_reverse_engineering\output\graph_top_nodes.html'
    if not os.path.exists(JSON_PATH): return
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    nodes_map = data.get('nodes', {})
    edges_list = data.get('edges', [])
    print("[*] Preparing FULL graph...")
    full_nodes = [{"id": n, "label": n, "plm_type": i.get('plm_type', 'Unknown'), "color": {"background": "#444", "border": "#888"}} for n, i in nodes_map.items()]
    full_edges = [{"from": e['source'], "to": e['target'], "label": e['type'], "color": {"color": "#2B7CE9" if e['type'] == 'bom_component' else "#D62728", "highlight": "#2B7CE9" if e['type'] == 'bom_component' else "#D62728"}} for e in edges_list]
    generate_html_file(full_nodes, full_edges, HTML_OUTPUT_FULL)
    print("[*] Preparing TOP-LEVEL graph...")
    out_deg = {}
    for e in edges_list:
        out_deg[e['source']] = out_deg.get(e['source'], 0) + 1
    top_names = sorted(out_deg.items(), key=lambda x: x[1], reverse=True)[:50]
    top_set = {n for n, c in top_names}
    filtered_set = set(top_set)
    for e in edges_list:
        if e['source'] in top_set: filtered_set.add(e['target'])
    f_nodes = [{"id": n, "label": n, "plm_type": nodes_map[n].get('plm_type', 'Unknown'), "color": {"background": "#444", "border": "#888"}} for n in filtered_set if n in nodes_map]
    f_edges = [{"from": e['source'], "to": e['target'], "label": e['type'], "color": {"color": "#2B7CE9" if e['type'] == 'bom_component' else "#D62728", "highlight": "#2B7CE9" if e['type'] == 'bom_component' else "#D62728"}} for e in edges_list if e['source'] in filtered_set and e['target'] in filtered_set]
    generate_html_file(f_nodes, f_edges, HTML_OUTPUT_TOP)

if __name__ == "__main__":
    run()

