"""Portable Win32 search fakes; native search behavior still needs Windows."""

import unittest

from filewheel.platforms.windows.name_ambiguity import probe_name_ambiguity


def winerror(code):
    error = OSError("fixture")
    error.winerror = code
    return error


class Search:
    def __init__(self, wildcard=(), *, exact="photo.png", first_error=None,
                 next_error=None, close_error=False):
        self.wildcard = list(wildcard)
        self.exact = exact
        self.first_error = first_error
        self.next_error = next_error
        self.close_error = close_error
        self.patterns = []
        self.closed = []
        self.next_calls = 0

    def first(self, pattern):
        self.patterns.append(pattern)
        if len(self.patterns) == 1:
            return 1, self.exact
        if self.first_error is not None:
            raise winerror(self.first_error)
        if not self.wildcard:
            raise winerror(2)
        return 2, self.wildcard.pop(0)

    def next(self, handle):
        self.next_calls += 1
        if self.next_error is not None:
            raise winerror(self.next_error)
        return self.wildcard.pop(0) if self.wildcard else None

    def close(self, handle):
        self.closed.append(handle)
        if self.close_error:
            raise winerror(6)


class NameAmbiguityTests(unittest.TestCase):
    def run_probe(self, search, path="C:/folder/photo.png", name="photo.png"):
        return probe_name_ambiguity(path, name, backend=search)

    def test_no_matching_extended_name_is_unique(self):
        search = Search()
        result = self.run_probe(search)
        self.assertEqual(result["status"], "unique")
        self.assertEqual(result["query_count"], 2)
        self.assertEqual(search.closed, [1])
        self.assertEqual(search.patterns, [r"C:\folder\photo.png", r"C:\folder\photo.png.*"])

    def test_dos_pattern_matching_candidate_itself_ends_cleanly(self):
        search = Search(["photo.png"])
        result = self.run_probe(search)
        self.assertEqual(result["status"], "unique")
        self.assertEqual(result["query_count"], 3)
        self.assertEqual(search.closed, [1, 2])

    def test_conflicting_long_name_or_short_alias_rejects(self):
        for found in ("photo.png.txt", "unrelated-long-name.txt", "PHOTO.PNG"):
            with self.subTest(found=found):
                search = Search([found])
                self.assertEqual(self.run_probe(search)["status"], "ambiguous")
                self.assertEqual(search.closed, [1, 2])
                self.assertEqual(search.next_calls, 0)

    def test_second_result_caps_consumption_even_for_thousands_of_collisions(self):
        search = Search(["photo.png"] + ["photo.png.txt"] * 1000)
        self.assertEqual(self.run_probe(search)["status"], "ambiguous")
        self.assertEqual(search.next_calls, 1)
        self.assertEqual(len(search.wildcard), 999)
        self.assertEqual(search.closed, [1, 2])

    def test_repeated_result_without_end_is_not_complete(self):
        self.assertEqual(self.run_probe(Search(["photo.png", "photo.png"]))["status"], "ambiguous")

    def test_first_query_error_only_file_not_found_means_no_wildcard_matches(self):
        for code in (3, 5, 18, 87):
            with self.subTest(code=code):
                search = Search(first_error=code)
                self.assertEqual(self.run_probe(search)["status"], "unproven")
                self.assertEqual(search.closed, [1])

    def test_next_or_close_error_fails_closed(self):
        for search in (Search(["photo.png"], next_error=5), Search(close_error=True)):
            with self.subTest(search=search):
                self.assertEqual(self.run_probe(search)["status"], "unproven")
                self.assertTrue(search.closed)

    def test_exact_sibling_query_rejects_alias(self):
        search = Search(exact="other.png")
        self.assertEqual(self.run_probe(search)["status"], "ambiguous")
        self.assertEqual(search.closed, [1])
        self.assertEqual(len(search.patterns), 1)

    def test_hidden_extensions_and_unsafe_patterns_never_query(self):
        for path, name in (
            ("C:/folder/photo.png", "photo"), ("C:/folder/photo*.png", "photo*.png"),
            ("C:/folder/photo.png:stream", "photo.png:stream"),
            ("//server/share/photo.png", "photo.png"),
            ("C:/folder/../photo.png", "photo.png"),
        ):
            with self.subTest(path=path, name=name):
                search = Search()
                self.assertEqual(self.run_probe(search, path, name)["status"], "unproven")
                self.assertEqual(search.patterns, [])

    def test_unicode_and_spaces_pass_literal_patterns(self):
        name = "Æ photo.png"
        search = Search(exact=name)
        result = self.run_probe(search, f"C:/folder/{name}", name)
        self.assertEqual(result["status"], "unique")
        self.assertTrue(search.patterns[1].endswith(name + ".*"))
