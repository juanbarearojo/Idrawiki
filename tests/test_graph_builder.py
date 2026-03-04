import unittest

from src.config import PipelineConfig
from src.graph_builder import GraphBuilder


class GraphBuilderTests(unittest.TestCase):
    def test_get_cooccurrence_edges_builds_window_pairs(self) -> None:
        edges = GraphBuilder.get_cooccurrence_edges(["a", "b", "c"], window_size=2)
        self.assertEqual(edges, [("a", "b"), ("b", "c")])

    def test_build_word_graph_without_pruning_keeps_words_and_bigrams(self) -> None:
        config = PipelineConfig(enable_word_pruning=False, top_n_bigrams=5)
        builder = GraphBuilder(config)

        graph = builder.build_word_graph(
            words_data=[("article-1", ["pain", "pain", "relief", "dose", "risk"])],
            bigrams_data=[("article-1", ["pain relief", "relief dose"])],
        )

        self.assertIn("pain", graph.nodes)
        self.assertIn("pain relief", graph.nodes)
        self.assertEqual(graph.nodes["pain"]["Attribute"], 2)
        self.assertTrue(graph.has_edge("pain relief", "pain"))
        self.assertTrue(graph.has_edge("pain relief", "relief"))

    def test_build_word_graph_with_pruning_removes_low_frequency_words(self) -> None:
        config = PipelineConfig(
            enable_word_pruning=True,
            top_n_bigrams=0,
            node_prune_percentile=50,
            min_node_freq=2,
            edge_prune_percentile=0,
            min_edge_weight=1,
        )
        builder = GraphBuilder(config)

        graph = builder.build_word_graph(
            words_data=[("article-1", ["common", "common", "rare", "rare", "solo"])],
            bigrams_data=[],
        )

        self.assertIn("common", graph.nodes)
        self.assertIn("rare", graph.nodes)
        self.assertNotIn("solo", graph.nodes)

    def test_build_link_graph_creates_directed_edges(self) -> None:
        graph = GraphBuilder.build_link_graph(
            {"source": {"target-1", "target-2"}}
        )
        self.assertTrue(graph.has_edge("source", "target-1"))
        self.assertEqual(graph.nodes["source"]["Group"], "link")
        self.assertEqual(graph["source"]["target-1"]["Type"], "Directed")


if __name__ == "__main__":
    unittest.main()
