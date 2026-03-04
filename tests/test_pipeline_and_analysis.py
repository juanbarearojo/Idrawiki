import argparse
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import pipeline
from src.exporter import GraphExporter
from src.greedy_mod import (
    aplicar_modularidad_codiciosa,
    construir_grafo,
    parse_args as parse_greedy_args,
)
from src.top_modularity import analizar_modularidad


class PipelineEntryPointTests(unittest.TestCase):
    def test_parse_args_reads_custom_cli_values(self) -> None:
        test_argv = [
            "pipeline.py",
            "--base-url",
            "https://es.wikipedia.org",
            "--seed-article",
            "Medicina",
            "--max-articles",
            "20",
            "--disable-link-pruning",
        ]

        with patch("sys.argv", test_argv):
            args = pipeline.parse_args()

        self.assertEqual(args.base_url, "https://es.wikipedia.org")
        self.assertEqual(args.seed_article, "Medicina")
        self.assertEqual(args.max_articles, 20)
        self.assertTrue(args.disable_link_pruning)

    def test_build_config_translates_cli_flags(self) -> None:
        args = argparse.Namespace(
            base_url="https://es.wikipedia.org",
            seed_article="Medicina",
            seed_url=None,
            max_articles=15,
            max_depth=2,
            min_link_freq=2,
            top_n_bigrams=50,
            edge_prune_percentile=25,
            node_prune_percentile=5,
            min_node_freq=2,
            min_edge_weight=2,
            spacy_model="custom_model",
            output_dir="custom_output",
            disable_link_pruning=True,
            disable_word_pruning=False,
        )

        config = pipeline.build_config(args)

        self.assertEqual(config.base_url, "https://es.wikipedia.org")
        self.assertEqual(config.seed_article, "Medicina")
        self.assertEqual(config.output_dir, Path("custom_output"))
        self.assertFalse(config.enable_link_pruning)
        self.assertTrue(config.enable_word_pruning)
        self.assertEqual(config.spacy_model, "custom_model")


class ExportVisitedArticlesTests(unittest.TestCase):
    def test_export_visited_articles_writes_one_url_per_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "visited.txt"
            GraphExporter.export_visited_articles(
                ["https://example.org/a", "https://example.org/b"],
                output_path,
            )

            content = output_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(content, ["https://example.org/a", "https://example.org/b"])


class CommunityAnalysisTests(unittest.TestCase):
    def test_construir_grafo_and_aplicar_modularidad_codiciosa(self) -> None:
        nodes_df = pd.DataFrame(
            [
                {"Id": 1, "Label": "a", "Group": "word", "Attribute": 3},
                {"Id": 2, "Label": "b", "Group": "word", "Attribute": 2},
                {"Id": 3, "Label": "c", "Group": "word", "Attribute": 2},
            ]
        )
        edges_df = pd.DataFrame(
            [
                {"Source": 1, "Target": 2, "Type": "Undirected", "Weight": 3},
                {"Source": 2, "Target": 3, "Type": "Undirected", "Weight": 2},
            ]
        )

        graph = construir_grafo(nodes_df, edges_df)
        communities, modularity = aplicar_modularidad_codiciosa(graph)

        self.assertEqual(graph.number_of_nodes(), 3)
        self.assertEqual(graph.number_of_edges(), 2)
        self.assertGreaterEqual(len(communities), 1)
        self.assertIsInstance(modularity, float)

    def test_analizar_modularidad_prints_summary_for_valid_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "metrics.csv"
            pd.DataFrame(
                [
                    {"Id": 1, "Label": "alpha", "degree": 5, "modularity_class": 0},
                    {"Id": 2, "Label": "beta", "degree": 3, "modularity_class": 0},
                    {"Id": 3, "Label": "gamma", "degree": 7, "modularity_class": 1},
                ]
            ).to_csv(csv_path, index=False)

            captured = io.StringIO()
            with patch("sys.stdout", captured):
                analizar_modularidad(str(csv_path), top_n=2)

        output = captured.getvalue()
        self.assertIn("Comunidad 1", output)
        self.assertIn("Clase de modularidad", output)
        self.assertIn("Top 10 nodos con mayor grado", output)

    def test_parse_args_for_greedy_mod_accepts_custom_paths(self) -> None:
        test_argv = [
            "greedy_mod.py",
            "--nodes",
            "custom_nodes.csv",
            "--edges",
            "custom_edges.csv",
        ]

        with patch("sys.argv", test_argv):
            args = parse_greedy_args()

        self.assertEqual(args.nodes, "custom_nodes.csv")
        self.assertEqual(args.edges, "custom_edges.csv")


if __name__ == "__main__":
    unittest.main()
