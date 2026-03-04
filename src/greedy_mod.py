import argparse

import networkx as nx
import pandas as pd
from networkx.algorithms.community import greedy_modularity_communities


def cargar_datos(nodos_path: str, aristas_path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    nodos_df = pd.read_csv(nodos_path)
    aristas_df = pd.read_csv(aristas_path)
    return nodos_df, aristas_df


def construir_grafo(nodos_df: pd.DataFrame, aristas_df: pd.DataFrame) -> nx.Graph:
    grafo = nx.Graph()
    for _, row in nodos_df.iterrows():
        grafo.add_node(row["Id"], label=row["Label"], group=row["Group"], attribute=row["Attribute"])
    for _, row in aristas_df.iterrows():
        grafo.add_edge(row["Source"], row["Target"], type=row["Type"], weight=row["Weight"])
    return grafo


def aplicar_modularidad_codiciosa(grafo: nx.Graph) -> tuple[list[list[int]], float]:
    comunidades = greedy_modularity_communities(grafo)
    comunidades_lista = [list(comunidad) for comunidad in comunidades]
    modularidad = nx.algorithms.community.quality.modularity(grafo, comunidades)
    return comunidades_lista, modularidad


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aplica modularidad codiciosa sobre un grafo exportado por el pipeline."
    )
    parser.add_argument("--nodes", default="data/words/words_bigrams_nodes.csv")
    parser.add_argument("--edges", default="data/words/words_bigrams_edges.csv")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    nodos_df, aristas_df = cargar_datos(args.nodes, args.edges)
    grafo = construir_grafo(nodos_df, aristas_df)

    if grafo.number_of_edges() == 0:
        print("El grafo no tiene aristas. No se puede aplicar la deteccion de comunidades.")
        return

    print("Aplicando el algoritmo de modularidad codiciosa...\n")
    comunidades, modularidad = aplicar_modularidad_codiciosa(grafo)

    print("=== Resultados Finales ===")
    print(f"Mejor modularidad: {modularidad:.4f}")
    print(f"Numero de comunidades: {len(comunidades)}")
    print("\nComunidades detectadas:")
    for index, comunidad in enumerate(comunidades, start=1):
        print(f" - Comunidad {index}: {len(comunidad)} nodos")


if __name__ == "__main__":
    main()
