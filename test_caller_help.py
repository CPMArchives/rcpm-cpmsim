"""Validate shipped command coverage and qualified-menu safety without old code."""
from pathlib import Path
import json
import unittest
from caller_help import validate_topics

ROOT = Path(__file__).resolve().parent


class HelpTests(unittest.TestCase):
    def setUp(self):
        self.topics = {p.name: p.read_text(encoding='ascii')
                       for p in (ROOT/'guest/help').glob('*.HLP')}

    def test_shipped_topics_and_access_coverage(self):
        validate_topics(self.topics)
        coverage = json.loads((ROOT/'docs/command-help-coverage.json').read_text())
        self.assertEqual(len(self.topics), 120)
        self.assertEqual(sum(row['kind'] == 'COM' for row in coverage), 63)
        self.assertEqual(sum(row['kind'] != 'COM' for row in coverage), 24)
        for row in coverage:
            topic = self.topics[row['topic']+'.HLP']
            if row['access'] == 'SYSOP ONLY':
                self.assertIn('SYSOP ONLY', topic)
                self.assertTrue(topic.splitlines()[1].startswith('* '))

    def test_one_letter_title_and_paginated_body(self):
        validate_topics({'H.HLP': ';\nH - RESIDENT COMMAND LIST\nA - Read\n:A\n'+('text\n'*60)})

    def test_qualified_target(self):
        validate_topics({'ROOT.HLP': ';\nRoot\nA - child\n:A:HELP:H.HLP\n',
                         'H.HLP': ';\nH - List\nA - read\n:A\ntext\n'})

    def test_missing_target_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Missing HELP target'):
            validate_topics({'ROOT.HLP': ';\nRoot\nA - child\n:A:HELP:NONE.HLP\n'})

    def test_ambiguous_unqualified_target_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Invalid HELP directive'):
            validate_topics({'ROOT.HLP': ';\nRoot\nA - child\n:A:H.HLP\n'})

    def test_menu_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, 'menu/directive mismatch'):
            validate_topics({'ROOT.HLP': ';\nRoot\nB - read\n:A\ntext\n'})

    def test_oversized_index_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Oversized HELP index'):
            validate_topics({'ROOT.HLP': ';\nRoot\n'+('\n'*20)+'A - read\n:A\ntext\n'})


if __name__ == '__main__':
    unittest.main()
