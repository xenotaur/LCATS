"""Corpus extractor for the Hemingway stories."""

from bs4 import BeautifulSoup

import lcats.gatherers.downloaders as downloaders


MEN_WITHOUT_WOMEN_GUTENBERG = 'https://www.gutenberg.org/cache/epub/69683/pg69683-images.html'


MEN_WITHOUT_WOMEN_HEADINGS = [
    ('undefeated', 'THE UNDEFEATED', 'Hemingway - the Undefeated'),
    ('in_another_country', 'IN ANOTHER COUNTRY', 'Hemingway - In Another Country'),
    ('hills_like_white_elephants', 'HILLS LIKE WHITE ELEPHANTS', 'Hemingway - Hills Like White Elephants'),
    ('killers', 'THE KILLERS', 'Hemingway - the Killers'),
    ('che_ti_dice_la_patria?', 'CHE TI DICE LA PATRIA?', 'Hemingway - Che Ti Dice La Patria?'),
    ('fifty_grand', 'FIFTY GRAND', 'Hemingway - Fifty Grand'),
    ('simple_enquiry', 'A SIMPLE ENQUIRY', 'Hemingway - a Simple Enquiry'),
    ('ten_indians', 'TEN INDIANS', 'Hemingway - Ten Indians'),
    ('canary_for_one', 'A CANARY FOR ONE', 'Hemingway - a Canary For One'),
    ('alpine_idyll', 'AN ALPINE IDYLL', 'Hemingway - An Alpine Idyll'),
    ('pursuit_race', 'A PURSUIT RACE', 'Hemingway - a Pursuit Race'),
    ('to-day_is_friday', 'TO-DAY IS FRIDAY', 'Hemingway - To-day is Friday'),
    ('banal_story', 'BANAL STORY', 'Hemingway - Banal Story'),
    ('now_i_lay_me', 'NOW I LAY ME', 'Hemingway - Now I Lay Me')
]
    
def find_paragraphs_menwithoutwomen(soup, start_heading_text):
    """Find paragraphs following a specific heading in a BeautifulSoup object."""
    # Find the start heading - this is brittle and may need to be adjusted for different stories

    start_heading = soup.find(
        lambda tag: tag.name in ('h1', 'h2') and start_heading_text in tag.get_text(strip=True))
    
    if start_heading is None:
        return None

    # If we got the heading, try to return the paragraphs following it
    paragraphs = []
    current_element = start_heading.find_next()

    # Iterate through sibling elements until the next heading or the end of the siblings is reached.
    while current_element and current_element.name not in ('h1'):   # removed div
        if current_element.name == 'p':
            paragraphs.append(current_element.get_text(strip=False))

        if  current_element.name == 'div':
            if current_element.get('class') != None and 'blockquote' in current_element.get('class'):
                paragraphs.append(current_element.get_text(strip=False))
            else:
                break

        if current_element.name == 'hr':
            current_element = current_element.find_next()
        else:
            current_element = current_element.find_next_sibling()
            
    return '\n'.join(paragraphs)


def create_download_callback(story_name, url, start_heading_text, description):
    """Create a download callback function for a specific story."""
    def story_download_callback(contents):
        """Download a specific Hemingway story from the Gutenberg Project."""

        if contents is None:
            raise ValueError(f"Failed to download {url}")

        story_soup = BeautifulSoup(contents, "lxml")

        story_text = find_paragraphs_menwithoutwomen(story_soup, start_heading_text)
        if story_text is None:
            raise ValueError(
                f"Failed to find text for {story_name} given {start_heading_text} in {url}")
        
        story_data = {
            "author": "Hemingway",
            "year": 1927,
            "url": url,
            "name": story_name,
        }

        return description, story_text, story_data

    return story_download_callback


def gather():
    """Run DataGatherers    for the Hemingway corpus."""
    gatherer = downloaders.DataGatherer(
        "hemingway", 
        description="Hemingway stories from the Gutenberg Project.",
        license="Public domain, from Project Gutenberg.")
    for filename, heading, title in MEN_WITHOUT_WOMEN_HEADINGS:
        gatherer.download(
            filename,
            MEN_WITHOUT_WOMEN_GUTENBERG,
            create_download_callback(
                story_name=filename,
                url=MEN_WITHOUT_WOMEN_GUTENBERG,
                start_heading_text=heading,
                description=title))
    return gatherer.downloads


def main():
    """Extract the Hemingway stories from the Gutenberg Project."""
    print("Gathering Hemingway stories.")
    downloads = gather()
    print(f" - Total stories in Hemingway corpus: {len(downloads)}")


if __name__ == "__main__":
    main()
