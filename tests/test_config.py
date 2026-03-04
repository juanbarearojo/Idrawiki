import unittest
from pathlib import Path

from src.config import PipelineConfig


class PipelineConfigTests(unittest.TestCase):
    def test_start_url_uses_seed_article(self) -> None:
        config = PipelineConfig(base_url="https://es.wikipedia.org", seed_article="Inteligencia artificial")
        self.assertEqual(
            config.start_url,
            "https://es.wikipedia.org/wiki/Inteligencia_artificial",
        )

    def test_seed_url_overrides_base_url_and_article(self) -> None:
        config = PipelineConfig(
            base_url="https://en.wikipedia.org",
            seed_article="Ignored",
            seed_url="https://fr.wikipedia.org/wiki/Paris",
        )
        self.assertEqual(config.start_url, "https://fr.wikipedia.org/wiki/Paris")
        self.assertEqual(config.resolved_base_url, "https://fr.wikipedia.org")

    def test_output_directories_are_derived_from_output_dir(self) -> None:
        config = PipelineConfig(output_dir=Path("custom_data"))
        self.assertEqual(config.words_output_dir, Path("custom_data") / "words")
        self.assertEqual(config.links_output_dir, Path("custom_data") / "links")
        self.assertEqual(config.visited_nodes_path, Path("custom_data") / "nodos_visitados.txt")


if __name__ == "__main__":
    unittest.main()
