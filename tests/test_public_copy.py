import html
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
CJK = r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]"
CJK_ADJACENT_HALF_WIDTH_PUNCTUATION = re.compile(rf"(?:{CJK}[,;:?]|[,;:?]{CJK})")
MARKDOWN_HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)\s*$", re.MULTILINE)


def extract_readme_chinese(text):
    before_license, separator, _ = text.partition("\n## License")
    if not separator:
        raise ValueError("README Chinese section must end before ## License")
    _, separator, chinese = before_license.partition("\n## 中文\n")
    if not separator:
        raise ValueError("README must contain a ## 中文 section")
    return chinese


def markdown_headings(text):
    return [
        (len(match.group(1)), match.group(2), match.start(), match.end())
        for match in MARKDOWN_HEADING.finditer(text)
    ]


def section_body(text, heading, headings):
    level, _, _, end = heading
    next_heading = next(
        (
            candidate
            for candidate in headings
            if candidate[2] > end and candidate[0] <= level
        ),
        None,
    )
    return text[end:next_heading[2] if next_heading else len(text)]


class LandingLanguageExtractor(HTMLParser):
    VOID_ELEMENTS = {
        "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr",
    }

    def __init__(self, language):
        super().__init__(convert_charrefs=False)
        self.language = language
        self.parts = []
        self.stack = []

    def _is_selected(self):
        return bool(self.stack) and self.stack[-1][1] == self.language

    def handle_starttag(self, tag, attrs):
        inherited_language = self.stack[-1][1] if self.stack else None
        node_language = next(
            (value for name, value in attrs if name.lower() == "data-lang"),
            inherited_language,
        )
        if node_language == self.language:
            self.parts.append(self.get_starttag_text())
        if tag not in self.VOID_ELEMENTS:
            self.stack.append((tag, node_language))

    def handle_startendtag(self, tag, attrs):
        if self._is_selected() or any(
            name.lower() == "data-lang" and value == self.language
            for name, value in attrs
        ):
            self.parts.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1][0] != tag:
            return
        _, node_language = self.stack.pop()
        if node_language == self.language:
            self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        if self._is_selected():
            self.parts.append(data)

    def handle_entityref(self, name):
        if self._is_selected():
            self.parts.append(f"&{name};")

    def handle_charref(self, name):
        if self._is_selected():
            self.parts.append(f"&#{name};")


def extract_landing_language(text, language):
    parser = LandingLanguageExtractor(language)
    parser.feed(text)
    parser.close()
    return "".join(parser.parts)


def extract_landing_chinese(text):
    if not re.search(r'<main\b[^>]*\bdata-lang=["\']zh["\']', text, re.IGNORECASE):
        raise ValueError("Landing page must contain <main data-lang=\"zh\">")
    return extract_landing_language(text, "zh")


def attr_value(attrs, name):
    return next(
        (value for attr_name, value in attrs if attr_name.lower() == name),
        None,
    )


def node_signature(tag, attrs):
    normalized_attrs = []
    for name, value in attrs:
        name = name.lower()
        if name == "data-lang":
            continue
        if name == "class":
            value = " ".join(
                sorted(token for token in (value or "").split() if token != "on")
            )
            if not value:
                continue
        normalized_attrs.append((name, value or ""))
    return tag, tuple(sorted(normalized_attrs))


class LandingStructureExtractor(HTMLParser):
    VOID_ELEMENTS = LandingLanguageExtractor.VOID_ELEMENTS

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.stack = []
        self.main_roots = {"en": [], "zh": []}
        self.main_children = {"en": [], "zh": []}
        self.cta_hrefs = {"en": [], "zh": []}
        self.header_nodes = {
            "tagline": {"en": [], "zh": []},
            "sub": {"en": [], "zh": []},
        }
        self.header_containers = []
        self.footer_containers = []
        self.footer_roots = {"en": [], "zh": []}
        self.language_buttons = []
        self.hrefs = []

    def _active_main_language(self):
        for frame in reversed(self.stack):
            if frame["main_language"]:
                return frame["main_language"]
        return None

    def handle_starttag(self, tag, attrs):
        language = attr_value(attrs, "data-lang")
        parent = self.stack[-1]["tag"] if self.stack else None
        active_main_language = self._active_main_language()
        signature = node_signature(tag, attrs)

        if tag == "header":
            self.header_containers.append(signature)
        if tag == "footer":
            self.footer_containers.append(signature)

        if tag == "main" and language in self.main_roots:
            self.main_roots[language].append(signature)
        elif active_main_language and parent == "main":
            self.main_children[active_main_language].append(signature)

        if active_main_language and tag == "a":
            classes = (attr_value(attrs, "class") or "").split()
            if "cta" in classes:
                self.cta_hrefs[active_main_language].append(attr_value(attrs, "href"))

        if tag == "a":
            href = attr_value(attrs, "href")
            if href:
                self.hrefs.append(href)

        if tag == "p" and parent == "header" and language in self.main_roots:
            classes = (attr_value(attrs, "class") or "").split()
            for header_class in self.header_nodes:
                if header_class in classes:
                    self.header_nodes[header_class][language].append(signature)

        if tag == "p" and parent == "footer" and language in self.footer_roots:
            self.footer_roots[language].append(signature)

        if tag == "button":
            button_id = attr_value(attrs, "id")
            if button_id in {"btn-en", "btn-zh"}:
                self.language_buttons.append(
                    (button_id, attr_value(attrs, "aria-pressed"))
                )

        if tag not in self.VOID_ELEMENTS:
            self.stack.append(
                {
                    "tag": tag,
                    "main_language": language if tag == "main" else None,
                }
            )

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1]["tag"] == tag:
            self.stack.pop()


def extract_landing_structure(text):
    parser = LandingStructureExtractor()
    parser.feed(text)
    parser.close()
    return parser


def clean_prose(text):
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"<pre\b[^>]*>.*?</pre\s*>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<code\b[^>]*>.*?</code\s*>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"`[^`\n]*`", "", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s{0,3}>\s?", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*(?:[-+*]|\d+[.)])\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"(?<!\\)(?:\*\*|__|~~|[*_])", "", text)
    text = re.sub(r"https?://[^\s<>\]\)]+", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"<[^>]+>", "", html.unescape(text))


README_SOURCE = (ROOT / "README.md").read_text()
README_CHINESE = extract_readme_chinese(README_SOURCE)
LANDING_SOURCE = (ROOT / "docs" / "index.html").read_text()
LANDING_CHINESE = extract_landing_chinese(LANDING_SOURCE)


class PublicCopyTests(unittest.TestCase):
    def test_docs_excludes_internal_process_records_and_internal_links(self):
        self.assertFalse((ROOT / "docs" / "superpowers").exists())
        for href in extract_landing_structure(LANDING_SOURCE).hrefs:
            with self.subTest(href=href):
                self.assertNotIn("planning/", href)
                self.assertNotIn("superpowers/", href)

    def test_public_copy_does_not_present_the_legacy_benchmark_as_current(self):
        for surface_name, surface in (
            ("README", README_SOURCE),
            ("landing page", LANDING_SOURCE),
        ):
            with self.subTest(surface=surface_name):
                self.assertNotIn("14/14", surface)
                self.assertNotIn("64%", surface)
                self.assertNotIn("no safety check", surface.lower())
                self.assertNotIn("没做安全检查", surface)

    def test_readme_has_paired_nonempty_language_sections(self):
        headings = markdown_headings(README_SOURCE)

        def level_two(title):
            return [heading for heading in headings if heading[:2] == (2, title)]

        english = level_two("English")
        chinese = level_two("中文")
        license_section = level_two("License")

        self.assertEqual(len(english), 1)
        self.assertEqual(len(chinese), 1)
        self.assertEqual(len(license_section), 1)
        self.assertLess(english[0][2], license_section[0][2])
        self.assertLess(chinese[0][2], license_section[0][2])
        self.assertTrue(section_body(README_SOURCE, english[0], headings).strip())
        self.assertTrue(section_body(README_SOURCE, chinese[0], headings).strip())

        english_heading_levels = [
            heading[0]
            for heading in headings
            if english[0][3] < heading[2] < chinese[0][2] and heading[0] >= 3
        ]
        chinese_heading_levels = [
            heading[0]
            for heading in headings
            if chinese[0][3] < heading[2] < license_section[0][2] and heading[0] >= 3
        ]
        self.assertEqual(english_heading_levels, chinese_heading_levels)
        self.assertTrue(english_heading_levels)

    def assert_nonempty_cta_hrefs(self, structure):
        for language in ("en", "zh"):
            for href in structure.cta_hrefs[language]:
                self.assertIsInstance(href, str, f"{language} CTA href")
                self.assertTrue(href.strip(), f"{language} CTA href")

    def assert_single_container(self, structure, attribute, tag):
        containers = getattr(structure, attribute, [])
        self.assertEqual(len(containers), 1)
        self.assertEqual([signature[0] for signature in containers], [tag])

    def test_landing_has_paired_language_structure(self):
        structure = extract_landing_structure(LANDING_SOURCE)

        for language in ("en", "zh"):
            with self.subTest(language=language):
                self.assertEqual(len(structure.main_roots[language]), 1)
                self.assertTrue(structure.main_children[language])
                self.assertTrue(structure.cta_hrefs[language])
                self.assertEqual(len(structure.header_nodes["tagline"][language]), 1)
                self.assertEqual(len(structure.header_nodes["sub"][language]), 1)
                self.assertEqual(len(structure.footer_roots[language]), 1)

        self.assert_nonempty_cta_hrefs(structure)
        self.assert_single_container(structure, "header_containers", "header")
        self.assert_single_container(structure, "footer_containers", "footer")
        self.assertEqual(structure.main_roots["en"], structure.main_roots["zh"])
        self.assertEqual(structure.main_children["en"], structure.main_children["zh"])
        self.assertEqual(structure.cta_hrefs["en"], structure.cta_hrefs["zh"])
        self.assertEqual(
            structure.header_nodes["tagline"]["en"],
            structure.header_nodes["tagline"]["zh"],
        )
        self.assertEqual(
            structure.header_nodes["sub"]["en"],
            structure.header_nodes["sub"]["zh"],
        )
        self.assertEqual(structure.footer_roots["en"], structure.footer_roots["zh"])
        self.assertEqual(
            structure.language_buttons,
            [("btn-en", "true"), ("btn-zh", "false")],
        )

        missing_href = extract_landing_structure(
            """\
<main data-lang="en" class="on"><a class="cta"></a></main>
<main data-lang="zh"><a class="cta"></a></main>
"""
        )
        with self.subTest(case="missing CTA href"):
            with self.assertRaises(AssertionError):
                self.assert_nonempty_cta_hrefs(missing_href)

        extra_containers = extract_landing_structure(
            LANDING_SOURCE.replace("</header>", "</header><header></header>", 1).replace(
                "</footer>", "</footer><footer></footer>", 1
            )
        )
        with self.subTest(case="extra empty containers"):
            self.assertEqual(
                len(getattr(extra_containers, "header_containers", [])), 2
            )
            self.assertEqual(
                len(getattr(extra_containers, "footer_containers", [])), 2
            )
            with self.assertRaises(AssertionError):
                self.assert_single_container(extra_containers, "header_containers", "header")
            with self.assertRaises(AssertionError):
                self.assert_single_container(extra_containers, "footer_containers", "footer")

    def test_landing_extractor_includes_footer_without_double_counting_nested_content(self):
        landing = """\
<main data-lang="zh">正文</main>
<footer><p data-lang="zh">页脚,文本</p></footer>
"""
        extracted = extract_landing_chinese(landing)

        self.assertEqual(extracted.count("页脚,文本"), 1)
        self.assertIsNotNone(
            CJK_ADJACENT_HALF_WIDTH_PUNCTUATION.search(clean_prose(extracted))
        )

        nested = """\
<p data-lang="zh">页眉</p>
<main data-lang="zh">正文<span data-lang="zh">嵌套内容</span></main>
<footer><p data-lang="zh">页脚</p></footer>
"""
        self.assertEqual(extract_landing_chinese(nested).count("嵌套内容"), 1)

    def test_landing_extractor_keeps_content_after_stray_void_end_tag(self):
        extracted = extract_landing_chinese(
            '<main data-lang="zh">可见<br></br>后续,文本</main>'
        )

        self.assertIn("后续", extracted)
        self.assertIsNotNone(
            CJK_ADJACENT_HALF_WIDTH_PUNCTUATION.search(clean_prose(extracted))
        )

    def test_chinese_prose_has_no_half_width_punctuation_touching_cjk(self):
        for surface_name, surface in (("README", README_CHINESE), ("landing page", LANDING_CHINESE)):
            with self.subTest(surface=surface_name):
                self.assertIsNone(
                    CJK_ADJACENT_HALF_WIDTH_PUNCTUATION.search(clean_prose(surface))
                )


if __name__ == "__main__":
    unittest.main()
