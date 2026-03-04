from __future__ import annotations

import random
import time
from collections import Counter, deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable
from urllib.parse import quote, unquote, urljoin, urlparse

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
    NON_CONTENT_NAMESPACES = {
        "category",
        "especial",
        "special",
        "file",
        "archivo",
        "help",
        "ayuda",
        "template",
        "plantilla",
        "user",
        "usuario",
        "talk",
        "discusion",
        "mediawiki",
        "module",
        "modulo",
        "forum",
        "thread",
        "comment",
        "blog",
        "widget",
    }

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
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,"
                    "image/avif,image/webp,*/*;q=0.8"
                ),
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            }
        )
        return session

    @staticmethod
    def _extract_article_name(path: str) -> str | None:
        marker = "/wiki/"
        lowered = path.lower()
        if marker not in lowered:
            return None
        index = lowered.rfind(marker)
        return path[index + len(marker) :]

    @classmethod
    def is_valid_article_title(cls, title: str) -> bool:
        if not title:
            return False

        normalized = title.strip()
        normalized_main = normalized.replace(" ", "_")
        if not normalized or normalized_main.lower() == "main_page":
            return False

        namespace = normalized.split(":", 1)[0].strip().lower() if ":" in normalized else ""
        if namespace and namespace in cls.NON_CONTENT_NAMESPACES:
            return False
        return True

    @classmethod
    def is_valid_article_url(cls, url: str, base_url: str) -> bool:
        parsed_url = urlparse(url)
        parsed_base = urlparse(base_url)

        if parsed_url.netloc != parsed_base.netloc:
            return False
        if parsed_url.fragment or parsed_url.query:
            return False

        article_name = cls._extract_article_name(parsed_url.path)
        if not article_name:
            return False
        article_title = unquote(article_name).replace("_", " ")
        return cls.is_valid_article_title(article_title)

    @staticmethod
    def _api_endpoint_candidates(base_url: str) -> list[str]:
        parsed = urlparse(base_url)
        root = f"{parsed.scheme}://{parsed.netloc}"
        return [f"{root}/api.php", f"{root}/w/api.php"]

    @staticmethod
    def _build_article_url(base_url: str, article_title: str) -> str:
        parsed = urlparse(base_url)
        root = f"{parsed.scheme}://{parsed.netloc}"
        slug = quote(article_title.replace(" ", "_"), safe=":()/_-.,'%")
        return f"{root}/wiki/{slug}"

    @classmethod
    def _extract_links_from_api_parse(cls, parse_data: dict[str, object], base_url: str) -> set[str]:
        links: set[str] = set()
        parse_links = parse_data.get("links", [])
        if not isinstance(parse_links, list):
            return links

        for item in parse_links:
            if not isinstance(item, dict):
                continue
            title = item.get("*")
            if not isinstance(title, str):
                continue
            if not cls.is_valid_article_title(title):
                continue

            article_url = cls._build_article_url(base_url, title)
            if cls.is_valid_article_url(article_url, base_url):
                links.add(article_url)
        return links

    @classmethod
    def extract_wikipedia_links(cls, soup: BeautifulSoup, base_url: str) -> set[str]:
        links: set[str] = set()
        for link in soup.find_all("a", href=True):
            normalized_url = urljoin(base_url, link["href"])
            if cls.is_valid_article_url(normalized_url, base_url):
                links.add(normalized_url)
        return links

    def _fetch_page_via_api(self, current_url: str) -> tuple[str, set[str]] | None:
        parsed_url = urlparse(current_url)
        article_name = self._extract_article_name(parsed_url.path)
        if not article_name:
            return None

        article_title = unquote(article_name).replace("_", " ")
        if not self.is_valid_article_title(article_title):
            return None

        for endpoint in self._api_endpoint_candidates(self.config.resolved_base_url):
            try:
                response = self.session.get(
                    endpoint,
                    params={
                        "action": "parse",
                        "page": article_title,
                        "prop": "text|links",
                        "format": "json",
                        "formatversion": 2,
                    },
                    timeout=self.config.request_timeout,
                )
            except requests.exceptions.RequestException:
                continue

            if response.status_code != 200:
                continue
            if "json" not in response.headers.get("Content-Type", "").lower():
                continue

            try:
                payload = response.json()
            except ValueError:
                continue

            if "error" in payload:
                continue

            parse_data = payload.get("parse")
            if not isinstance(parse_data, dict):
                continue

            parsed_html = parse_data.get("text", "")
            html = parsed_html if isinstance(parsed_html, str) else ""
            links = self._extract_links_from_api_parse(parse_data, self.config.resolved_base_url)
            return html, links

        return None

    def _fetch_page_via_html(self, current_url: str) -> tuple[str, set[str]] | None:
        try:
            response = self.session.get(current_url, timeout=self.config.request_timeout)
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            print(f"Error al solicitar {current_url}: {exc}")
            return None

        if "html" not in response.headers.get("Content-Type", ""):
            print(f"El contenido no es HTML para {current_url}")
            return None

        soup = BeautifulSoup(response.content, "html.parser")
        html = str(soup)
        links = self.extract_wikipedia_links(soup, self.config.resolved_base_url)
        return html, links

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
        blocked_domains: set[str] = set()

        source_mode = self.config.source_mode.lower().strip()
        if source_mode not in {"auto", "api", "html"}:
            print(f"source_mode '{self.config.source_mode}' invalido. Se usara 'auto'.")
            source_mode = "auto"

        while visit_queue and total_articles < self.config.max_articles:
            current_url, depth = visit_queue.popleft()
            if current_url in visited_articles or depth > self.config.max_depth:
                continue

            print(f"Scraping: {current_url} (Depth: {depth})")
            time.sleep(random.uniform(self.config.min_request_delay, self.config.max_request_delay))

            html_content: str | None = None
            links: set[str] | None = None

            if source_mode in {"auto", "api"}:
                api_result = self._fetch_page_via_api(current_url)
                if api_result:
                    html_content, links = api_result

            if html_content is None and source_mode in {"auto", "html"}:
                html_result = self._fetch_page_via_html(current_url)
                if html_result:
                    html_content, links = html_result

            if html_content is None or links is None:
                blocked_domains.add(urlparse(current_url).netloc)
                continue

            soup_for_text = BeautifulSoup(html_content, "html.parser")
            text = " ".join(paragraph.get_text() for paragraph in soup_for_text.find_all("p"))
            words, bigrams = self.text_processor.clean_text(text)
            words_data.append((current_url, words))
            bigrams_data.append((current_url, bigrams))

            print(f"Palabras extraidas: {len(words)}")
            print(f"Bigrams extraidos: {len(bigrams)}")
            links_data.append((current_url, links))
            print(f"Enlaces encontrados: {len(links)}")

            for link in links:
                if link not in visited_articles and depth + 1 <= self.config.max_depth:
                    visit_queue.append((link, depth + 1))

            visited_articles.add(current_url)
            total_articles += 1
            print(f"Total de articulos procesados: {total_articles}/{self.config.max_articles}\n")

        if blocked_domains:
            print(
                "Dominios con paginas no procesadas (posible bloqueo/403 o API no disponible): "
                + ", ".join(sorted(blocked_domains))
            )

        final_links = dict(links_data)
        if self.config.enable_link_pruning:
            final_links = self.prune_links(links_data, self.config.min_link_freq)

        return CrawlResult(
            words_data=words_data,
            bigrams_data=bigrams_data,
            links_data=final_links,
            visited_articles=sorted(visited_articles),
        )
