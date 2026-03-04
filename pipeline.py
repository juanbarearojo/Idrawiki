import argparse
import json
import sys
from pathlib import Path

from src.config import PipelineConfig


def load_config_file(config_path: str | Path | None) -> dict[str, object]:
    if not config_path:
        return {}

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"No se encontro el archivo de configuracion: {path}")

    with path.open(encoding="utf-8") as config_file:
        loaded = json.load(config_file)

    if not isinstance(loaded, dict):
        raise ValueError("El archivo de configuracion debe contener un objeto JSON.")

    valid_keys = PipelineConfig.field_names()
    unknown_keys = set(loaded.keys()) - valid_keys
    if unknown_keys:
        raise ValueError(
            "Claves no soportadas en el archivo de configuracion: "
            + ", ".join(sorted(unknown_keys))
        )

    return loaded


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scrapea Wikipedia y genera redes de palabras, bigramas y enlaces."
    )
    parser.add_argument("--config", default="pipeline_config.json")
    parser.add_argument("--base-url", default=argparse.SUPPRESS)
    parser.add_argument("--seed-article", default=argparse.SUPPRESS)
    parser.add_argument("--seed-url", help="URL completa del articulo inicial. Tiene prioridad.", default=argparse.SUPPRESS)
    parser.add_argument("--max-articles", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--max-depth", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--min-link-freq", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--top-n-bigrams", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--edge-prune-percentile", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--node-prune-percentile", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--min-node-freq", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--min-edge-weight", type=int, default=argparse.SUPPRESS)
    parser.add_argument("--spacy-model", default=argparse.SUPPRESS)
    parser.add_argument("--output-dir", default=argparse.SUPPRESS)
    parser.add_argument("--disable-link-pruning", action="store_true", default=argparse.SUPPRESS)
    parser.add_argument("--disable-word-pruning", action="store_true", default=argparse.SUPPRESS)
    return parser


def parse_args() -> argparse.Namespace:
    parser = build_parser()
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> PipelineConfig:
    default_config = PipelineConfig().to_dict()
    file_config = load_config_file(getattr(args, "config", None))
    merged_config = default_config | file_config

    cli_values = vars(args).copy()
    cli_values.pop("config", None)

    if "disable_link_pruning" in cli_values:
        cli_values["enable_link_pruning"] = not cli_values.pop("disable_link_pruning")
    if "disable_word_pruning" in cli_values:
        cli_values["enable_word_pruning"] = not cli_values.pop("disable_word_pruning")

    if "output_dir" in merged_config:
        merged_config["output_dir"] = Path(merged_config["output_dir"])
    if "output_dir" in cli_values:
        cli_values["output_dir"] = Path(cli_values["output_dir"])

    merged_config.update(cli_values)
    return PipelineConfig(**merged_config)


def main() -> None:
    args = parse_args()
    config = build_config(args)

    try:
        from src.exporter import GraphExporter
        from src.graph_builder import GraphBuilder
        from src.text_processing import WikipediaTextProcessor
        from src.wikipedia_crawler import WikipediaCrawler

        config.ensure_output_dirs()

        print("=== Wikipedia Scraper and Network Generator ===\n")
        print("=== Configuracion cargada ===")
        print(f"Articulo inicial: {config.start_url}")
        print(f"URL base: {config.resolved_base_url}")
        print(f"Profundidad maxima: {config.max_depth}")
        print(f"Maximo de articulos: {config.max_articles}")
        print(f"Poda de enlaces: {'activa' if config.enable_link_pruning else 'desactivada'}")
        print(f"Poda de red textual: {'activa' if config.enable_word_pruning else 'desactivada'}")
        print(f"Salida palabras: {config.words_output_dir}")
        print(f"Salida enlaces: {config.links_output_dir}\n")

        text_processor = WikipediaTextProcessor(config.spacy_model)
        crawler = WikipediaCrawler(config, text_processor)
        graph_builder = GraphBuilder(config)

        print("Iniciando el proceso de scraping...\n")
        crawl_result = crawler.crawl()

        if not crawl_result.words_data:
            print("No se recopilaron datos de palabras.")
        if not crawl_result.bigrams_data:
            print("No se recopilaron datos de bigramas.")
        if not crawl_result.links_data:
            print("No se recopilaron datos de enlaces.")

        print("\nGenerando la red de palabras y bigramas...")
        words_graph = graph_builder.build_word_graph(
            crawl_result.words_data, crawl_result.bigrams_data
        )

        print("\nGenerando la red de hipervinculos...")
        links_graph = graph_builder.build_link_graph(crawl_result.links_data)

        print("\nExportando resultados...")
        GraphExporter.export_graph(
            words_graph,
            config.words_output_dir / "words_bigrams_nodes.csv",
            config.words_output_dir / "words_bigrams_edges.csv",
            graph_type="word_bigram",
        )
        GraphExporter.export_graph(
            links_graph,
            config.links_output_dir / "links_nodes.csv",
            config.links_output_dir / "links_edges.csv",
            graph_type="link",
        )
        GraphExporter.export_visited_articles(
            crawl_result.visited_articles, config.visited_nodes_path
        )

        print("\n=== Exportacion completada ===")
        print(
            "Nodos y aristas de palabras y bigrams guardados en "
            f"{config.words_output_dir}"
        )
        print(
            "Nodos y aristas de hipervinculos guardados en "
            f"{config.links_output_dir}"
        )
        print(f"Nodos visitados guardados en {config.visited_nodes_path}")
    except Exception as exc:
        print(f"Ocurrio un error inesperado: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
