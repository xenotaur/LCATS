import unittest
from bs4 import BeautifulSoup

from lcats.gatherers import extractors


class TestExtractor(unittest.TestCase):
    """Unit tests for the extractors.Extractor class."""

    def test_init_basic(self):
        """Basic construction with required fields."""
        extractor = extractors.Extractor("My Story", "http://example.com/story")
        self.assertEqual(extractor.title, "My Story")
        self.assertEqual(extractor.url, "http://example.com/story")
        self.assertEqual(extractor.file, "my_story")
        self.assertIsNone(extractor.author)
        self.assertIsNone(extractor.year)

    def test_init_with_optional_fields(self):
        """Construction with all optional fields provided."""
        extractor = extractors.Extractor(
            "My Story", "http://example.com/story", file="custom_file", author="Jane Doe", year=2021
        )
        self.assertEqual(extractor.file, "custom_file")
        self.assertEqual(extractor.author, "Jane Doe")
        self.assertEqual(extractor.year, 2021)

    def test_description_with_author(self):
        """Description includes author when provided."""
        extractor = extractors.Extractor("My Story", "http://example.com/story", author="Jane Doe")
        self.assertEqual(extractor.description, "My Story by Jane Doe")

    def test_description_without_author(self):
        """Description is just the title when no author is provided."""
        extractor = extractors.Extractor("My Story", "http://example.com/story")
        self.assertEqual(extractor.description, "My Story")

    def test_repr_with_author(self):
        """Repr includes description with author."""
        extractor = extractors.Extractor("My Story", "http://example.com/story", author="Jane Doe")
        self.assertEqual(repr(extractor), "Extractor('My Story by Jane Doe')")

    def test_repr_without_author(self):
        """Repr includes title when no author is provided."""
        extractor = extractors.Extractor("My Story", "http://example.com/story")
        self.assertEqual(repr(extractor), "Extractor('My Story')")


class TestTitleToFilename(unittest.TestCase):
    """Unit tests for the extractors.title_to_filename function."""

    def test_simple_title(self):
        """Basic filename extraction."""
        self.assertEqual(
            extractors.title_to_filename("The Call of Cthulhu"), "the_call_of_cthulhu"
        )

    def test_title_with_special_characters(self):
        """Filename extraction with removal of special characters."""
        self.assertEqual(
            extractors.title_to_filename("The Case of Charles Dexter Ward!"),
            "the_case_of_charles_dexter_ward",
        )

    def test_title_with_multiple_spaces(self):
        """Collapse multiple spaces."""
        self.assertEqual(
            extractors.title_to_filename("  A Tale   of Two Cities  "),
            "a_tale_of_two_cities",
        )

    def test_title_with_punctuation(self):
        """Remove punctuation."""
        self.assertEqual(
            extractors.title_to_filename("The Strange Case of Dr. Jekyll & Mr. Hyde"),
            "the_strange_case_of_dr_jekyll_mr_hyde",
        )

    def test_title_with_non_alpha_numeric(self):
        """Remove non-alphanumeric characters."""
        self.assertEqual(
            extractors.title_to_filename("The King's Speech!"), "the_kings_speech"
        )

    def test_title_with_numbers(self):
        """Keep numbers in the title."""
        self.assertEqual(extractors.title_to_filename("1984: A Novel"), "1984_a_novel")

    def test_empty_string(self):
        """Return an empty string for an empty title."""
        self.assertEqual(extractors.title_to_filename(""), "")

    def test_title_with_only_special_characters(self):
        """Return an empty string for a title with only special characters."""
        self.assertEqual(extractors.title_to_filename("!!!..."), "")


class TestExtractors(unittest.TestCase):
    """Tests for the extractors module."""

    def setUp(self):
        """Set up the test environment."""
        # Example HTML content to test against
        self.html_content = """
        <div>
            <h2>Introduction</h2>
            <p>Welcome to the introduction.</p>
            <h2>Body</h2>
            <p>This is the body section paragraph one.</p>
            <p>This is the body section paragraph two.</p>
            <div>
                <h3>Subsection</h3>
                <p>This is a subsection within the body.</p>
            </div>
            <h2>Conclusion</h2>
            <p>Final thoughts.</p>
        </div>
        """
        self.soup = BeautifulSoup(self.html_content, "html.parser")

    def test_get_section_text_from_headings_basic(self):
        """Test extracting a section with headings."""
        result = extractors.get_section_text_from_headings(self.soup, "Body")
        expected_text = (
            "This is the body section paragraph one.\n"
            "This is the body section paragraph two."
        )
        self.assertEqual(result, expected_text)

    def test_get_section_text_from_headings_with_subsection(self):
        """Test extracting a section with subsections included."""
        result = extractors.get_section_text_from_headings(
            self.soup,
            "Body",
            section_body_tags=["p", "div"],
            end_section_tags=["h2", "h3"],
        )
        expected_text = (
            "This is the body section paragraph one.\n"
            "This is the body section paragraph two.\n"
            "Subsection\n"
            "This is a subsection within the body."
        )
        self.assertEqual(result, expected_text)

    def test_get_section_text_from_headings_no_section(self):
        """Test extracting a non-existent section."""
        result = extractors.get_section_text_from_headings(self.soup, "Nonexistent")
        self.assertIsNone(result)

    def test_get_section_text_from_headings_different_tags(self):
        """Test with different heading and body tags."""
        result = extractors.get_section_text_from_headings(
            self.soup, "Subsection", start_heading_tags=["h3"], end_section_tags=["h2"]
        )
        expected_text = "This is a subsection within the body."
        self.assertEqual(result, expected_text)

    def test_get_section_text_no_start_heading(self):
        """Test extractors.get_section_text directly when no start heading is found."""

        def is_section_start(tag):
            return tag.name == "h1" and "Nonexistent" in tag.get_text()

        result = extractors.get_section_text(
            self.soup, is_section_start, lambda x: False, lambda x: x.name == "p"
        )
        self.assertIsNone(result)

    def test_get_section_text_no_end_section(self):
        """Test extraction with no end tag to stop at."""

        def is_section_start(tag):
            return tag.name == "h2" and "Body" in tag.get_text()

        result = extractors.get_section_text(
            self.soup, is_section_start, lambda x: False, lambda x: x.name == "p"
        )
        expected_text = (
            "This is the body section paragraph one.\n"
            "This is the body section paragraph two.\n"
            "Final thoughts."
        )
        self.assertEqual(result, expected_text)

    def test_get_section_text_includes_div(self):
        """Test extraction with a div inside the section."""

        def is_section_start(tag):
            return tag.name == "h2" and "Body" in tag.get_text()

        result = extractors.get_section_text(
            self.soup,
            is_section_start,
            lambda x: x.name == "h2" and "Conclusion" in x.get_text(),
            lambda x: x.name == "p",
        )
        expected_text = "This is the body section paragraph one.\nThis is the body section paragraph two."
        self.assertEqual(result, expected_text)

    def test_extract_tags_between_ids_present(self):
        """Test extract_tags_between_ids for tags between two IDs."""
        # Add start and end IDs to test specific section extraction
        start_tag = self.soup.find("h2", text="Body")
        start_tag["id"] = "pg-start-separator"
        end_tag = self.soup.find("h2", text="Conclusion")
        end_tag["id"] = "pg-end-separator"

        # Extract tags between the start and end
        tags = extractors.extract_tags_between_ids(
            self.soup, "pg-start-separator", "pg-end-separator", ["p", "h3"]
        )

        # Expected tags and text between "Body" and "Conclusion"
        expected_texts = [
            "This is the body section paragraph one.",
            "This is the body section paragraph two.",
            "Subsection",
            "This is a subsection within the body.",
        ]

        # Check extracted tags count
        self.assertEqual(len(tags), 4)
        # Check the content of each extracted tag
        for tag, expected_text in zip(tags, expected_texts):
            self.assertEqual(tag.get_text(strip=True), expected_text)

    def test_extract_tags_between_ids_absent(self):
        """Test extract_tags_between_ids for tags between two IDs."""
        # Extract tags between the start and end
        tags = extractors.extract_tags_between_ids(
            self.soup, "pg-start-separator", "pg-end-separator", ["p", "h3"]
        )

        # We should not get any tags if the start or end IDs are missing
        self.assertIsNone(tags)

    def test_extract_text_from_tags_with_tags(self):
        """Test extract_text_from_tags for proper concatenation of tag text."""
        # Sample tags to extract text from
        tags = [self.soup.new_tag("p")]
        tags[0].string = "This is a sample paragraph."

        additional_tag = self.soup.new_tag("p")
        additional_tag.string = "This is another paragraph."
        tags.append(additional_tag)

        # Expected output with default separator
        expected_text = "This is a sample paragraph.\n\nThis is another paragraph."

        # Extract text and check the result
        extracted_text = extractors.extract_text_from_tags(tags)
        self.assertEqual(extracted_text, expected_text)

    def test_extract_text_from_tags_empty(self):
        """Test extract_text_from_tags for proper concatenation of tag text."""
        # Sample tags to extract text from
        tags = []

        # Expected output even with default separator should be empty.
        expected_text = ""

        # Extract text and check the result
        extracted_text = extractors.extract_text_from_tags(tags)
        self.assertEqual(extracted_text, expected_text)

    def test_extract_text_between_ids(self):
        """Test extract_text_between_ids to get full section text between IDs."""
        # Add start and end IDs to test specific section extraction
        start_tag = self.soup.find("h2", text="Body")
        start_tag["id"] = "pg-start-separator"
        end_tag = self.soup.find("h2", text="Conclusion")
        end_tag["id"] = "pg-end-separator"

        # Extract text between the start and end tags
        extracted_text = extractors.extract_text_between_ids(
            self.soup, "pg-start-separator", "pg-end-separator", ["p", "h3"]
        )

        # Expected text with paragraphs and subsections separated by double newlines
        expected_text = (
            "This is the body section paragraph one.\n\n"
            "This is the body section paragraph two.\n\n"
            "Subsection\n\n"
            "This is a subsection within the body."
        )

        # Check if the extracted text matches the expected output
        self.assertEqual(extracted_text, expected_text)


if __name__ == "__main__":
    unittest.main()
