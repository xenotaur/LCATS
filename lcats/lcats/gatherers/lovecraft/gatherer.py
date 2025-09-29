"""Corpus extractor for the Lovecraft stories."""

from bs4 import BeautifulSoup

import lcats.gatherers.downloaders as downloaders
import lcats.gatherers.extractors as extractors


def make_extractor(title, url, author="H. P. Lovecraft"):
    """Create an Extractor for a Lovecraft story."""
    return extractors.Extractor(title, url, author=author)


THE_LOVECRAFT_FILES = [make_extractor(*params) for params in [
    ('The Call of Cthulhu', 'https://www.gutenberg.org/cache/epub/68283/pg68283-images.html'),
    ('The Dunwich Horror', 'https://www.gutenberg.org/cache/epub/50133/pg50133-images.html'),
    ('At the Mountains of Madness', 'https://www.gutenberg.org/cache/epub/70652/pg70652-images.html'),
    ('The Shadow over Innsmouth', 'https://www.gutenberg.org/cache/epub/73181/pg73181-images.html'),
    ('The Colour out of Space', 'https://www.gutenberg.org/cache/epub/68236/pg68236-images.html'),
    ('The Shunned House', 'https://www.gutenberg.org/cache/epub/31469/pg31469-images.html'),
    ('The Case of Charles Dexter Ward', 'https://www.gutenberg.org/cache/epub/73547/pg73547-images.html'),
    ('The Horror at Red Hook', 'https://www.gutenberg.org/cache/epub/72966/pg72966-images.html'),
    ('The Thing on the Door-Step', 'https://www.gutenberg.org/cache/epub/73230/pg73230-images.html'),
    ('The Festival', 'https://www.gutenberg.org/cache/epub/68553/pg68553-images.html'),
    ('The Haunter of the Dark', 'https://www.gutenberg.org/cache/epub/73233/pg73233-images.html'),
    ('The Lurking Fear', 'https://www.gutenberg.org/cache/epub/70486/pg70486-images.html'),
    ('Through the Gates of the Silver Key', 'https://www.gutenberg.org/cache/epub/71167/pg71167-images.html'),
    ('The Silver Key', 'https://www.gutenberg.org/cache/epub/70478/pg70478-images.html'),
    ('Cool Air', 'https://www.gutenberg.org/cache/epub/73177/pg73177-images.html'),
    ('The Quest of Iranon', 'https://www.gutenberg.org/cache/epub/73182/pg73182-images.html'),
    ('He', 'https://www.gutenberg.org/cache/epub/68547/pg68547-images.html'),
]]

# Need to find the URLs for these stories:
# The Whisperer in Darkness
# The Dreams in the Witch-House
# The Shadow out of Time
# The Ritual
# Collaborations:
# Medusa's Coil: https://www.gutenberg.org/cache/epub/70899/pg70899-images.html
# The Trap: https://www.gutenberg.org/cache/epub/73243/pg73243-images.html
# The Curse of Yig: https://www.gutenberg.org/cache/epub/70912/pg70912-images.html: 


def create_download_callback(extractor):
    """Create a download callback function for a specific story."""
    def story_download_callback(contents):
        """Download a specific Lovecraft story from the Gutenberg Project."""
        if contents is None:
            raise ValueError(f"Failed to download {extractor.url}")

        story_soup = BeautifulSoup(contents, "lxml")
    
        story_text = extractors.extract_text_between_ids(story_soup)
        if story_text is None:
            raise ValueError(
                f"Failed to find text for {extractor.title} given {extractor.title} in {extractor.url}")

        story_data = {
            "author": extractor.author,
            "year": 1925,
            "url": extractor.url,
            "name": extractor.title,
        }

        return extractor.description, story_text, story_data

    return story_download_callback


def gather():
    """Run DataGatherers for the Lovecraft corpus."""
    gatherer = downloaders.DataGatherer(
        "lovecraft",
        description="Lovecraft stories from the Gutenberg Project.",
        license="Public domain, from Project Gutenberg.")
    for extractor in THE_LOVECRAFT_FILES:
        gatherer.download(
            extractor.file,
            extractor.url,
            create_download_callback(extractor))
    return gatherer.downloads


def main():
    """Extract the Lovecraft stories from the Gutenberg Project."""
    print("Gathering Lovecraft stories.")
    downloads = gather()
    print(f" - Total stories in Lovecraft corpus: {len(downloads)}")


if __name__ == "__main__":
    main()
