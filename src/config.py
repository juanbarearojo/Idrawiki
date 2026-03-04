from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlparse


@dataclass
class PipelineConfig:
    base_url: str = "https://en.wikipedia.org"
    seed_article: str = "Fentanyl"
    seed_url: str | None = None
    max_articles: int = 100
    max_depth: int = 100
    min_link_freq: int = 3
    top_n_bigrams: int = 150
    edge_prune_percentile: int = 45
    node_prune_percentile: int = 15
    min_node_freq: int = 5
    min_edge_weight: int = 5
    request_timeout: int = 10
    min_request_delay: float = 1.0
    max_request_delay: float = 3.0
    spacy_model: str = "en_core_sci_md"
    source_mode: str = "auto"
    enable_link_pruning: bool = True
    enable_word_pruning: bool = True
    output_dir: Path = Path("data")

    @property
    def start_url(self) -> str:
        if self.seed_url:
            return self.seed_url

        article_slug = quote(self.seed_article.replace(" ", "_"))
        return f"{self.base_url.rstrip('/')}/wiki/{article_slug}"

    @property
    def resolved_base_url(self) -> str:
        if self.seed_url:
            parsed = urlparse(self.seed_url)
            return f"{parsed.scheme}://{parsed.netloc}"
        return self.base_url.rstrip("/")

    @property
    def words_output_dir(self) -> Path:
        return self.output_dir / "words"

    @property
    def links_output_dir(self) -> Path:
        return self.output_dir / "links"

    @property
    def visited_nodes_path(self) -> Path:
        return self.output_dir / "nodos_visitados.txt"

    def ensure_output_dirs(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.words_output_dir.mkdir(parents=True, exist_ok=True)
        self.links_output_dir.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def field_names(cls) -> set[str]:
        return set(cls.__dataclass_fields__.keys())
