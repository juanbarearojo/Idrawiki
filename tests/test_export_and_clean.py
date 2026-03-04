import csv
import tempfile
import unittest
from pathlib import Path

import networkx as nx
import pandas as pd

from src.clean_links_csv import clean_labels
from src.exporter import GraphExporter


class ExportAndCleanTests(unittest.TestCase):
    def test_export_graph_writes_nodes_and_edges_csv(self) -> None:
        graph = nx.Graph()
        graph.add_node("alpha", Group="word", Attribute=3)
        graph.add_node("beta", Group="word", Attribute=2)
        graph.add_edge("alpha", "beta", Type="Undirected", Weight=4)

        with tempfile.TemporaryDirectory() as tmp_dir:
            nodes_path = Path(tmp_dir) / "nodes.csv"
            edges_path = Path(tmp_dir) / "edges.csv"
            GraphExporter.export_graph(graph, nodes_path, edges_path)

            with nodes_path.open(newline="", encoding="utf-8") as nodes_file:
                rows = list(csv.reader(nodes_file))
            with edges_path.open(newline="", encoding="utf-8") as edges_file:
                edge_rows = list(csv.reader(edges_file))

        self.assertEqual(rows[0], ["Id", "Label", "Group", "Attribute"])
        self.assertEqual(edge_rows[0], ["Source", "Target", "Type", "Weight"])
        self.assertEqual(len(rows), 3)
        self.assertEqual(len(edge_rows), 2)

    def test_clean_labels_removes_base_url_and_quotes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / "links.csv"
            output_path = Path(tmp_dir) / "links_clean.csv"
            pd.DataFrame(
                [{"Label": '"https://es.wikipedia.org/wiki/Medicina"', "Id": 1, "Group": "link", "Attribute": 0}]
            ).to_csv(input_path, index=False)

            clean_labels(str(input_path), str(output_path), "https://es.wikipedia.org")
            cleaned = pd.read_csv(output_path)

        self.assertEqual(cleaned.loc[0, "Label"], "Medicina")


if __name__ == "__main__":
    unittest.main()
