import networkx as nx
import plotly.graph_objects as go
from plotly.io import to_json


def create_knowledge_graph(df):
    """
    create nx Graph from DataFrame relations data
    """
    G = nx.Graph()
    for _, row in df.iterrows():
        source = row["source"]
        target = row["target"]
        attributes = {k: v for k, v in row.items() if k not in ["source", "target"]}
        G.add_edge(source, target, **attributes)

    return G


def visualize_graph(G):
    pos = nx.spring_layout(G, dim=2)

    edge_x = []
    edge_y = []
    edge_texts = nx.get_edge_attributes(G, "description")
    to_display_edge_texts = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.append(x0)
        edge_x.append(x1)
        edge_x.append(None)
        edge_y.append(y0)
        edge_y.append(y1)
        edge_y.append(None)
        to_display_edge_texts.append(edge_texts[edge])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        text=to_display_edge_texts,
        line=dict(width=0.5, color="#888"),
        hoverinfo="text",
        mode="lines",
    )

    node_x = []
    node_y = []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)

    node_adjacencies = []
    node_text = []
    node_size = []
    for node_id, adjacencies in enumerate(G.adjacency()):
        degree = len(adjacencies[1])
        node_adjacencies.append(degree)
        node_text.append(adjacencies[0])
        node_size.append(15 if degree < 5 else (30 if degree < 10 else 60))

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        textfont=dict(
            family="Courier New, monospace",
            size=10,  # Set the font size here
        ),
        textposition="top center",
        mode="markers+text",
        hoverinfo="text",
        text=node_text,
        marker=dict(
            showscale=True,
            # colorscale options
            size=node_size,
            colorscale="YlGnBu",
            reversescale=True,
            color=node_adjacencies,
            colorbar=dict(
                thickness=5,
                xanchor="left",
                titleside="right",
            ),
            line_width=2,
        ),
    )

    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            showlegend=False,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        ),
    )
    fig.update_layout(autosize=True)

    return to_json(fig)
