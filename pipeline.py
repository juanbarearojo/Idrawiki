import argparse
import sys
from pathlib import Path

from src.config import PipelineConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrapea Wikipedia y genera redes de palabras, bigramas y enlaces."
    )
    parser.add_argument("--base-url", default="https://en.wikipedia.org")
    parser.add_argument("--seed-article", default="Fentanyl")
    parser.add_argument("--seed-url", help="URL completa del articulo inicial. Tiene prioridad.")
    parser.add_argument("--max-articles", type=int, default=100)
    parser.add_argument("--max-depth", type=int, default=100)
    parser.add_argument("--min-link-freq", type=int, default=3)
    parser.add_argument("--top-n-bigrams", type=int, default=150)
    parser.add_argument("--edge-prune-percentile", type=int, default=45)
    parser.add_argument("--node-prune-percentile", type=int, default=15)
    parser.add_argument("--min-node-freq", type=int, default=5)
    parser.add_argument("--min-edge-weight", type=int, default=5)
    parser.add_argument("--spacy-model", default="en_core_sci_md")
    parser.add_argument("--output-dir", default="data")
    parser.add_argument("--disable-link-pruning", action="store_true")
    parser.add_argument("--disable-word-pruning", action="store_true")
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> PipelineConfig:
    return PipelineConfig(
        base_url=args.base_url,
        seed_article=args.seed_article,
        seed_url=args.seed_url,
        max_articles=args.max_articles,
        max_depth=args.max_depth,
        min_link_freq=args.min_link_freq,
        top_n_bigrams=args.top_n_bigrams,
        edge_prune_percentile=args.edge_prune_percentile,
        node_prune_percentile=args.node_prune_percentile,
        min_node_freq=args.min_node_freq,
        min_edge_weight=args.min_edge_weight,
        spacy_model=args.spacy_model,
        enable_link_pruning=not args.disable_link_pruning,
        enable_word_pruning=not args.disable_word_pruning,
        output_dir=Path(args.output_dir),
    )


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
