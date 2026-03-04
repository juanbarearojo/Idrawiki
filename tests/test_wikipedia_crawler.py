import unittest

from bs4 import BeautifulSoup

from src.wikipedia_crawler import WikipediaCrawler


class WikipediaCrawlerTests(unittest.TestCase):
    def test_extract_wikipedia_links_filters_non_article_links(self) -> None:
        html = """
        <html><body>
            <a href="/wiki/Fentanyl">ok</a>
            <a href="/wiki/Main_Page">main</a>
            <a href="/wiki/Help:Contents">help</a>
            <a href="/wiki/Article#Section">anchor</a>
            <a href="https://example.com/outside">outside</a>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")

        links = WikipediaCrawler.extract_wikipedia_links(soup, "https://en.wikipedia.org")

        self.assertEqual(links, {"https://en.wikipedia.org/wiki/Fentanyl"})

    def test_prune_links_keeps_only_repeated_targets(self) -> None:
        links_data = [
            ("a", {"shared", "unique-a"}),
            ("b", {"shared", "unique-b"}),
        ]

        pruned = WikipediaCrawler.prune_links(links_data, min_freq=2)

        self.assertEqual(pruned, {"a": {"shared"}, "b": {"shared"}})


if __name__ == "__main__":
    unittest.main()
