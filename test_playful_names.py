"""Run:  python -m unittest test_playful_names -v"""
import re
import unittest

import playful_names as pn
from avatars import AVATAR_CATALOG

USERNAME_RE = re.compile(r"^[a-z0-9._-]{3,80}$")   # same rule auth_routes.py enforces


class PlayfulNamesTests(unittest.TestCase):
    def test_fifty_words_total(self):
        self.assertEqual(len(pn.HAPPY_WORDS) + len(pn.ANIMALS), 50)

    def test_no_duplicate_words_or_overlap(self):
        words = pn.HAPPY_WORDS + pn.ANIMALS
        self.assertEqual(len(words), len({w.lower() for w in words}))

    def test_every_combination_is_a_valid_unique_username(self):
        seen = set()
        for h in pn.HAPPY_WORDS:
            for a in pn.ANIMALS:
                u = pn.username_for(h, a)
                self.assertRegex(u, USERNAME_RE)
                seen.add(u)
        self.assertEqual(len(seen), 625)

    def test_display_and_username_formats(self):
        self.assertEqual(pn.display_name("Jumping", "Chameleon"), "Jumping Chameleon")
        self.assertEqual(pn.username_for("Crazy", "Crab"), "crazy-crab")

    def test_pair_validation_rejects_anything_else(self):
        self.assertTrue(pn.is_valid_pair("Crazy", "Crab"))
        for h, a in (("Crab", "Crazy"), ("crazy", "Crab"), ("Crazy", "Dragon"), ("", ""), ("Crazy", None), ("Real", "Name")):
            with self.subTest(h=h, a=a):
                self.assertFalse(pn.is_valid_pair(h, a))


class AvatarCatalogTests(unittest.TestCase):
    def test_catalog_is_big_enough_and_unique(self):
        keys = [a["key"] for a in AVATAR_CATALOG]
        emoji = [a["emoji"] for a in AVATAR_CATALOG]
        self.assertGreaterEqual(len(keys), 60)          # avatars are one-per-person
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(emoji), len(set(emoji)))
        for a in AVATAR_CATALOG:
            self.assertTrue(a["label"] and a["emoji"])


if __name__ == "__main__":
    unittest.main()
