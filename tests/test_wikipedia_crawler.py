import unittest

from bs4 import BeautifulSoup

from src.wikipedia_crawler import WikipediaCrawler


class WikipediaCrawlerTests(unittest.TestCase):
    def test_api_endpoint_candidates_support_common_mediawiki_patterns(self) -> None:
        endpoints_wikipedia = WikipediaCrawler._api_endpoint_candidates("https://es.wikipedia.org/wiki/Foo")
        endpoints_fandom = WikipediaCrawler._api_endpoint_candidates("https://onepiece.fandom.com/es/wiki/Foo")
        self.assertEqual(
            endpoints_wikipedia,
            ["https://es.wikipedia.org/api.php", "https://es.wikipedia.org/w/api.php"],
        )
        self.assertEqual(
            endpoints_fandom,
            ["https://onepiece.fandom.com/api.php", "https://onepiece.fandom.com/w/api.php"],
        )

    def test_extract_article_name_supports_prefixed_paths(self) -> None:
        self.assertEqual(
            WikipediaCrawler._extract_article_name("/es/wiki/Monkey_D._Luffy"),
            "Monkey_D._Luffy",
        )
        self.assertEqual(
            WikipediaCrawler._extract_article_name("/wiki/Main_Page"),
            "Main_Page",
        )

    def test_extract_links_from_api_parse_filters_non_content_namespaces(self) -> None:
        parse_data = {
            "links": [
                {"*": "Monkey D. Luffy"},
                {"*": "Special:Search"},
                {"*": "Category:Pirates"},
                {"*": "One Piece Wiki:About"},
            ]
        }
        links = WikipediaCrawler._extract_links_from_api_parse(
            parse_data, "https://onepiece.fandom.com/es/wiki/One_Piece_Wiki"
        )
        self.assertIn("https://onepiece.fandom.com/wiki/Monkey_D._Luffy", links)
        self.assertIn("https://onepiece.fandom.com/wiki/One_Piece_Wiki:About", links)
        self.assertNotIn("https://onepiece.fandom.com/wiki/Special:Search", links)

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

    def test_extract_links_supports_fandom_es_wiki_paths(self) -> None:
        html = """
        <html><body>
            <a href="/es/wiki/Monkey_D._Luffy">contenido</a>
            <a href="/es/wiki/Special:Search">special</a>
            <a href="/es/wiki/Ayuda:Edicion">help</a>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")

        links = WikipediaCrawler.extract_wikipedia_links(
            soup, "https://onepiece.fandom.com/es/wiki/One_Piece_Wiki"
        )

        self.assertEqual(links, {"https://onepiece.fandom.com/es/wiki/Monkey_D._Luffy"})

    def test_extract_links_supports_bulbapedia_absolute_urls(self) -> None:
        html = """
        <html><body>
            <a href="https://bulbapedia.bulbagarden.net/wiki/Pikachu_(Pok%C3%A9mon)">ok</a>
            <a href="https://bulbapedia.bulbagarden.net/wiki/Help:Contents">help</a>
            <a href="https://bulbagarden.net">external</a>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")

        links = WikipediaCrawler.extract_wikipedia_links(
            soup, "https://bulbapedia.bulbagarden.net/wiki/Main_Page"
        )

        self.assertEqual(
            links,
            {"https://bulbapedia.bulbagarden.net/wiki/Pikachu_(Pok%C3%A9mon)"},
        )

    def test_extract_links_supports_wikidex_relative_paths(self) -> None:
        html = """
        <html><body>
            <a href="/wiki/Pok%C3%A9mon">ok</a>
            <a href="/wiki/Especial:Estad%C3%ADsticas">special</a>
            <a href="/wiki/WikiDex:Acerca_de">namespace permitido</a>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")

        links = WikipediaCrawler.extract_wikipedia_links(
            soup, "https://www.wikidex.net/wiki/WikiDex"
        )

        self.assertEqual(
            links,
            {
                "https://www.wikidex.net/wiki/Pok%C3%A9mon",
                "https://www.wikidex.net/wiki/WikiDex:Acerca_de",
            },
        )

    def test_extract_links_supports_coppermind_namespace_pages(self) -> None:
        html = """
        <html><body>
            <a href="/wiki/Coppermind:Ayuda">permitido</a>
            <a href="/wiki/Category:Magic">category</a>
            <a href="/wiki/Kelsier">ok</a>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")

        links = WikipediaCrawler.extract_wikipedia_links(
            soup, "https://es.coppermind.net/wiki/Coppermind:Bienvenidos"
        )

        self.assertEqual(
            links,
            {
                "https://es.coppermind.net/wiki/Coppermind:Ayuda",
                "https://es.coppermind.net/wiki/Kelsier",
            },
        )

    def test_is_valid_article_url_supports_warhammer_fandom(self) -> None:
        self.assertTrue(
            WikipediaCrawler.is_valid_article_url(
                "https://warhammer40k.fandom.com/wiki/Emperor_of_Mankind",
                "https://warhammer40k.fandom.com/wiki/Warhammer_40k_Wiki",
            )
        )
        self.assertFalse(
            WikipediaCrawler.is_valid_article_url(
                "https://warhammer40k.fandom.com/wiki/Special:Search",
                "https://warhammer40k.fandom.com/wiki/Warhammer_40k_Wiki",
            )
        )
        self.assertFalse(
            WikipediaCrawler.is_valid_article_url(
                "https://warhammer40k.fandom.com/wiki/Category:Space_Marines",
                "https://warhammer40k.fandom.com/wiki/Warhammer_40k_Wiki",
            )
        )

    def test_prune_links_keeps_only_repeated_targets(self) -> None:
        links_data = [
            ("a", {"shared", "unique-a"}),
            ("b", {"shared", "unique-b"}),
        ]

        pruned = WikipediaCrawler.prune_links(links_data, min_freq=2)

        self.assertEqual(pruned, {"a": {"shared"}, "b": {"shared"}})


if __name__ == "__main__":
    unittest.main()
