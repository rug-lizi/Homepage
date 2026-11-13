import copy
import unittest
from html.parser import HTMLParser

from scripts.build import launch_label, load_catalog, render_page, sorted_websites, validate


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.websites, self.repos = load_catalog()

    def test_latest_first_and_unknown_last(self):
        examples = [dict(self.websites[0], id='unknown', launch_date=None),
                    dict(self.websites[0], id='old', launch_date='2020-01-01'),
                    dict(self.websites[0], id='new', launch_date='2026-01-01')]
        self.assertEqual([s['id'] for s in sorted_websites(examples)], ['new', 'old', 'unknown'])

    def test_estimates_are_distinguishable(self):
        site = dict(self.websites[0], launch_date='2026-01-02', launch_estimated=True)
        self.assertEqual(launch_label(site), '约 2026-01-02 上线')
        site['launch_estimated'] = False
        self.assertEqual(launch_label(site), '2026-01-02 上线')

    def test_rejects_unsafe_urls_duplicates_and_missing_repositories(self):
        for change in ({'url': 'javascript:alert(1)'}, {'url': 'https://user:password@example.com'}, {'repository': 'missing-repo'}, {'launch_date': '2026-02-30'}):
            websites = copy.deepcopy(self.websites)
            websites[0].update(change)
            with self.assertRaises(ValueError):
                validate(websites, self.repos)
        with self.assertRaises(ValueError):
            validate(self.websites + [self.websites[0]], self.repos)

    def test_page_keeps_every_repository_and_listed_website(self):
        class Entries(HTMLParser):
            def __init__(self):
                super().__init__(); self.kinds = []
            def handle_starttag(self, tag, attrs):
                if tag == 'article': self.kinds.append(dict(attrs).get('data-kind'))
        parser = Entries()
        page = render_page(self.websites, self.repos)
        parser.feed(page)
        self.assertEqual(parser.kinds.count('repository'), len(self.repos['repositories']))
        self.assertEqual(parser.kinds.count('website'), sum(s['listed'] for s in self.websites))
        self.assertNotIn('class="cover"', page)
        self.assertIn('https://home.liyw.top/', page)

    def test_untrusted_metadata_is_escaped(self):
        websites = copy.deepcopy(self.websites)
        websites[0]['name'] = '<script>alert(1)</script>'
        page = render_page(websites, self.repos)
        self.assertNotIn('<script>alert(1)</script>', page)
        self.assertIn('&lt;script&gt;', page)


if __name__ == '__main__':
    unittest.main()
