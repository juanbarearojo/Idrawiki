from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

import networkx as nx


class GraphExporter:
    @staticmethod
    def export_graph(
        graph: nx.Graph, output_nodes: Path, output_edges: Path, graph_type: str = "word_bigram"
    ) -> None:
        node_ids = {node: index + 1 for index, node in enumerate(graph.nodes())}
        nx.set_node_attributes(graph, node_ids, "Id")

        print(f"Exportando nodos a {output_nodes}...")
        with output_nodes.open("w", newline="", encoding="utf-8") as nodes_file:
            writer = csv.writer(nodes_file)
            writer.writerow(["Id", "Label", "Group", "Attribute"])
            for node, data in graph.nodes(data=True):
                writer.writerow([data["Id"], node, data["Group"], data["Attribute"]])

        print(f"Exportando aristas a {output_edges}...")
        with output_edges.open("w", newline="", encoding="utf-8") as edges_file:
            writer = csv.writer(edges_file)
            writer.writerow(["Source", "Target", "Type", "Weight"])
            for source, target, data in graph.edges(data=True):
                source_id = graph.nodes[source]["Id"]
                target_id = graph.nodes[target]["Id"]
                edge_type = data.get(
                    "Type",
                    "Undirected" if graph_type in {"word", "bigram", "word_bigram"} else "Directed",
                )
                writer.writerow([source_id, target_id, edge_type, data.get("Weight", 1)])

    @staticmethod
    def export_visited_articles(visited_articles: Iterable[str], output_path: Path) -> None:
        print(f"Exportando nodos visitados a {output_path}...")
        with output_path.open("w", encoding="utf-8") as output_file:
            for article in visited_articles:
                output_file.write(f"{article}\n")
