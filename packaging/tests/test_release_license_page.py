import unittest
from html.parser import HTMLParser
from pathlib import Path


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.assert_no_handlers(attrs)
        if tag == 'a':
            self.links.append(dict(attrs).get('href', ''))

    @staticmethod
    def assert_no_handlers(attrs):
        assert not any(key.lower().startswith('on') for key, _ in attrs)


class LicensePageTest(unittest.TestCase):
    def test_generated_license_page_is_static_and_has_core_terms(self):
        root = Path(__file__).resolve().parents[2]
        page = root/'web'/'public'/'licenses'/'index.html'
        text = page.read_text(encoding='utf-8')
        parsed = Page()
        parsed.feed(text)
        self.assertNotIn('script', parsed.tags)
        self.assertNotIn('iframe', parsed.tags)
        self.assertNotIn('object', parsed.tags)
        self.assertIn('GNU AFFERO GENERAL PUBLIC LICENSE', text)
        self.assertIn('Intel Simplified Software License', text)
        self.assertIn('latex2mathml', text)
        for link in parsed.links:
            if not link.startswith(('https://', '/')):
                self.assertTrue((page.parent/link).is_file(), link)


if __name__ == '__main__':
    unittest.main()
