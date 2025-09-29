"""Corpus extractor for the Anderson stories."""

from bs4 import BeautifulSoup

import lcats.gatherers.downloaders as downloaders


ANDERSON_GUTENBERG = 'https://www.gutenberg.org/cache/epub/1597/pg1597-images.html'

ANDERSON_HEADINGS = [
    ("emperor's_new_clothes", "THE EMPEROR'S NEW CLOTHES", "Anderson - The Emperor's New Clothes"),
    ("swineherd", "THE SWINEHERD", "Anderson - The Swineherd"),
    ("real_princess", "THE REAL PRINCESS", "Anderson - The Real Princess"),
    ("shoes_of_fortune", "THE SHOES OF FORTUNE", "Anderson - The Shoes Of Fortune"),
    ("fir_tree", "THE FIR TREE", "Anderson - The Fir Tree"),
    ("snow_queen", "THE SNOW QUEEN", "Anderson - The Snow Queen"),
    ("leap-frog", "THE LEAP-FROG", "Anderson - The Leap-frog"),
    ("elderbush", "THE ELDERBUSH", "Anderson - The Elderbush"),
    ("bell", "THE BELL", "Anderson - The Bell"),
    ("old_house", "THE OLD HOUSE", "Anderson - The Old House"),
    ("happy_family", "THE HAPPY FAMILY", "Anderson - The Happy Family"),
    ("story_of_a_mother", "THE STORY OF A MOTHER", "Anderson - The Story Of a Mother"),
    ("false_collar", "THE FALSE COLLAR", "Anderson - The False Collar"),
    ("shadow", "THE SHADOW", "Anderson - The Shadow"),
    ("little_match_girl", "THE LITTLE MATCH GIRL", "Anderson - The Little Match Girl"),
    ("dream_of_little_tuk", "THE DREAM OF LITTLE TUK", "Anderson - The Dream Of Little Tuk"),
    ("naughty_boy", "THE NAUGHTY BOY", "Anderson - The Naughty Boy"),
    ("red_shoes", "THE RED SHOES", "Anderson - The Red Shoes")
]
    
def find_paragraphs_andersonfairytales(soup, start_heading_text):
    """Find paragraphs following a specific heading in a BeautifulSoup object."""
    # Find the start heading - this is brittle and may need to be adjusted for different stories
    start_heading = soup.find(
        lambda tag: tag.name in ('h2') and start_heading_text in tag.get_text(strip=True))

    if start_heading is None:
        return None
    
    # If we got the heading, try to return the paragraphs following it
    paragraphs = []
    current_element = start_heading.find_next_sibling()

    # Iterate through sibling elements until the next heading or the end of the siblings is reached.
    while current_element and current_element.name not in ('h2', 'div'):
        if current_element.name == 'p' or current_element.name == 'pre':
            paragraphs.append(current_element.get_text(strip=False))
        current_element = current_element.find_next_sibling()

    return '\n'.join(paragraphs)


def create_download_callback(story_name, url, start_heading_text, description):
    """Create a download callback function for a specific story."""
    def story_download_callback(contents):
        """Download a specific Anderson story from the Gutenberg Project."""

        if contents is None:
            raise ValueError(f"Failed to download {url}")

        story_soup = BeautifulSoup(contents, "lxml")

        story_text = find_paragraphs_andersonfairytales(story_soup, start_heading_text)
        if story_text is None:
            raise ValueError(
                f"Failed to find text for {story_name} given {start_heading_text} in {url}")
        
        story_data = {
            "author": "Anderson",
            "year": 1911,
            "url": url,
            "name": story_name,
        }

        return description, story_text, story_data

    return story_download_callback


def gather():
    """Run DataGatherers for the Anderson corpus."""
    gatherer = downloaders.DataGatherer(
        "anderson", 
        description="Anderson stories from the Gutenberg Project.",
        license="Public domain, from Project Gutenberg.")
    for filename, heading, title in ANDERSON_HEADINGS:
        gatherer.download(
            filename,
            ANDERSON_GUTENBERG,
            create_download_callback(
                story_name=filename,
                url=ANDERSON_GUTENBERG,
                start_heading_text=heading,
                description=title))
    return gatherer.downloads


def main():
    """Extract the Anderson stories from the Gutenberg Project."""
    print("Gathering Anderson stories.")
    downloads = gather()
    print(f" - Total stories in Anderson corpus: {len(downloads)}")


if __name__ == "__main__":
    main()
