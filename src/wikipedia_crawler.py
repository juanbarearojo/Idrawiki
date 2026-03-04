from __future__ import annotations

import random
import time
from collections import Counter, deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.config import PipelineConfig

if TYPE_CHECKING:
    from src.text_processing import WikipediaTextProcessor


@dataclass
class CrawlResult:
    words_data: list[tuple[str, list[str]]]
    bigrams_data: list[tuple[str, list[str]]]
    links_data: dict[str, set[str]]
    visited_articles: list[str]


class WikipediaCrawler:
    def __init__(self, config: PipelineConfig, text_processor: WikipediaTextProcessor) -> None:
        self.config = config
        self.text_processor = text_processor
        self.session = self._build_session()

    @staticmethod
    def _build_session() -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    @staticmethod
    def extract_wikipedia_links(soup: BeautifulSoup, base_url: str) -> set[str]:
        links: set[str] = set()
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if (
                href.startswith("/wiki/")
                and ":" not in href
                and not href.startswith("/wiki/Main_Page")
                and "#" not in href
            ):
                links.add(urljoin(base_url, href))
        return links

    @staticmethod
    def prune_links(links_data: Iterable[tuple[str, set[str]]], min_freq: int) -> dict[str, set[str]]:
        link_counter: Counter[str] = Counter()
        links_list = list(links_data)
        for _, links in links_list:
            link_counter.update(links)

        valid_links = {link for link, freq in link_counter.items() if freq >= min_freq}
        pruned_links_data: dict[str, set[str]] = {}
        for source, links in links_list:
            pruned = links.intersection(valid_links)
            if pruned:
                pruned_links_data[source] = pruned

        print(f"Enlaces retenidos despues de la poda: {len(pruned_links_data)}")
        return pruned_links_data

    def crawl(self) -> CrawlResult:
        visited_articles: set[str] = set()
        visit_queue = deque([(self.config.start_url, 0)])
        words_data: list[tuple[str, list[str]]] = []
        bigrams_data: list[tuple[str, list[str]]] = []
        links_data: list[tuple[str, set[str]]] = []
        total_articles = 0

        while visit_queue and total_articles < self.config.max_articles:
            current_url, depth = visit_queue.popleft()
            if current_url in visited_articles or depth > self.config.max_depth:
                continue

            print(f"Scraping: {current_url} (Depth: {depth})")
            time.sleep(random.uniform(self.config.min_request_delay, self.config.max_request_delay))

            try:
                response = self.session.get(current_url, timeout=self.config.request_timeout)
                response.raise_for_status()
            except requests.exceptions.RequestException as exc:
                print(f"Error al solicitar {current_url}: {exc}")
                continue

            if "html" not in response.headers.get("Content-Type", ""):
                print(f"El contenido no es HTML para {current_url}")
                continue

            soup = BeautifulSoup(response.content, "html.parser")
            text = " ".join(paragraph.get_text() for paragraph in soup.find_all("p"))
            words, bigrams = self.text_processor.clean_text(text)
            words_data.append((current_url, words))
            bigrams_data.append((current_url, bigrams))

            print(f"Palabras extraidas: {len(words)}")
            print(f"Bigrams extraidos: {len(bigrams)}")

            links = self.extract_wikipedia_links(soup, self.config.resolved_base_url)
            links_data.append((current_url, links))
            print(f"Enlaces encontrados: {len(links)}")

            for link in links:
                if link not in visited_articles and depth + 1 <= self.config.max_depth:
                    visit_queue.append((link, depth + 1))

            visited_articles.add(current_url)
            total_articles += 1
            print(f"Total de articulos procesados: {total_articles}/{self.config.max_articles}\n")

        final_links = dict(links_data)
        if self.config.enable_link_pruning:
            final_links = self.prune_links(links_data, self.config.min_link_freq)

        return CrawlResult(
            words_data=words_data,
            bigrams_data=bigrams_data,
            links_data=final_links,
            visited_articles=sorted(visited_articles),
        )
