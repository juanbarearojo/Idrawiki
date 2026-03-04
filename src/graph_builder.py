from __future__ import annotations

from collections import Counter

import networkx as nx
import numpy as np

from src.config import PipelineConfig


class GraphBuilder:
    def __init__(self, config: PipelineConfig) -> None:
        self.config = config

    @staticmethod
    def get_cooccurrence_edges(words: list[str], window_size: int = 5) -> list[tuple[str, str]]:
        edges: list[tuple[str, str]] = []
        for index in range(len(words) - window_size + 1):
            window = words[index : index + window_size]
            for left in range(len(window)):
                for right in range(left + 1, len(window)):
                    edges.append(tuple(sorted((window[left], window[right]))))
        return edges

    @staticmethod
    def prune_edges_by_percentile(
        graph: nx.Graph, percentile: int, min_weight: int
    ) -> nx.Graph:
        weights = [data["Weight"] for _, _, data in graph.edges(data=True)]
        if not weights:
            print("No hay aristas para podar.")
            return graph

        threshold = np.percentile(weights, percentile)
        edges_to_remove = [
            (source, target)
            for source, target, data in graph.edges(data=True)
            if data.get("Weight", 1) < threshold or data.get("Weight", 1) < min_weight
        ]
        graph.remove_edges_from(edges_to_remove)
        print(
            f"Umbral de poda de aristas (percentil {percentile}, peso minimo {min_weight}): {threshold}"
        )
        print(f"Aristas eliminadas durante la poda: {len(edges_to_remove)}")
        return graph

    @staticmethod
    def prune_nodes_by_percentile(
        graph: nx.Graph, percentile: int, min_freq: int
    ) -> nx.Graph:
        word_nodes = {
            node: data["Attribute"]
            for node, data in graph.nodes(data=True)
            if data["Group"] == "word"
        }
        if not word_nodes:
            print("No hay nodos de palabras para podar.")
            return graph

        frequencies = list(word_nodes.values())
        threshold = np.percentile(frequencies, percentile)
        nodes_to_remove = [
            node for node, freq in word_nodes.items() if freq < threshold or freq < min_freq
        ]
        graph.remove_nodes_from(nodes_to_remove)
        print(
            f"Umbral de poda de nodos (percentil {percentile}, frecuencia minima {min_freq}): {threshold}"
        )
        print(f"Nodos eliminados durante la poda: {len(nodes_to_remove)}")
        return graph

    def build_word_graph(
        self,
        words_data: list[tuple[str, list[str]]],
        bigrams_data: list[tuple[str, list[str]]],
    ) -> nx.Graph:
        graph = nx.Graph()
        word_freq_global: Counter[str] = Counter()
        edge_freq_global: Counter[tuple[str, str]] = Counter()
        bigram_freq_global: Counter[str] = Counter()

        for _, words in words_data:
            word_freq_global.update(Counter(words))
            edge_freq_global.update(Counter(self.get_cooccurrence_edges(words)))

        for _, bigrams in bigrams_data:
            bigram_freq_global.update(bigrams)

        for word, freq in word_freq_global.items():
            graph.add_node(word, Group="word", Attribute=freq)

        top_bigrams = bigram_freq_global.most_common(self.config.top_n_bigrams)
        for bigram, freq in top_bigrams:
            graph.add_node(bigram, Group="bigram", Attribute=freq)

        for (word1, word2), freq in edge_freq_global.items():
            if word1 in graph.nodes and word2 in graph.nodes:
                graph.add_edge(word1, word2, Type="Undirected", Weight=freq)

        for bigram, _ in top_bigrams:
            split_bigram = bigram.split()
            if len(split_bigram) != 2:
                print(f"Bigram invalido detectado: '{bigram}'")
                continue

            word1, word2 = split_bigram
            if word1 in graph.nodes and word2 in graph.nodes:
                graph.add_edge(bigram, word1, Type="Contains", Weight=1)
                graph.add_edge(bigram, word2, Type="Contains", Weight=1)

        print("\nConectando bigrams entre si basados en palabras compartidas...")
        for left in range(len(top_bigrams)):
            for right in range(left + 1, len(top_bigrams)):
                bigram1, _ = top_bigrams[left]
                bigram2, _ = top_bigrams[right]
                if set(bigram1.split()).intersection(bigram2.split()):
                    graph.add_edge(bigram1, bigram2, Type="Co-occurs", Weight=1)

        if self.config.enable_word_pruning:
            print("\nAplicando la poda de aristas...")
            graph = self.prune_edges_by_percentile(
                graph,
                percentile=self.config.edge_prune_percentile,
                min_weight=self.config.min_edge_weight,
            )

            print("\nAplicando la poda de nodos...")
            graph = self.prune_nodes_by_percentile(
                graph,
                percentile=self.config.node_prune_percentile,
                min_freq=self.config.min_node_freq,
            )

        return graph

    @staticmethod
    def build_link_graph(links_data: dict[str, set[str]]) -> nx.DiGraph:
        graph = nx.DiGraph()
        for source, targets in links_data.items():
            graph.add_node(source, Group="link", Attribute=0)
            for target in targets:
                graph.add_node(target, Group="link", Attribute=0)
                graph.add_edge(source, target, Type="Directed", Weight=1)
        return graph
