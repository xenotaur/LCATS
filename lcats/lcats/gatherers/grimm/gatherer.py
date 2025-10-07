"""Corpus extractor for the Grimm stories."""

from bs4 import BeautifulSoup

import lcats.gatherers.downloaders as downloaders

# The grimm book on gutenberg uses a bizarre bit of encoding for some
# characters.   Found help on using reg expr to convert the text at
# https://patrickwu.space/2017/11/09/python-encoding-issue/

import re


TARGET_DIRECTORY = "grimm"


GRIMM_GUTENBERG = 'https://www.gutenberg.org/cache/epub/2591/pg2591-images.html'


GRIMM_HEADINGS = [
    ('golden_bird', 'THE GOLDEN BIRD', 'Grimm - the Golden Bird'),
    ('hans_in_luck', 'HANS IN LUCK', 'Grimm - Hans In Luck'),
    ('jorinda_and_jorindel', 'JORINDA AND JORINDEL', 'Grimm - Jorinda And Jorindel'),
    ('travelling_musicians', 'THE TRAVELLING MUSICIANS',
     'Grimm - the Travelling Musicians'),
    ('old_sultan', 'OLD SULTAN', 'Grimm - Old Sultan'),
    ('straw,_the_coal,_and_the_bean', 'THE STRAW, THE COAL, AND THE BEAN',
     'Grimm - the Straw, the Coal, And the Bean'),
    ('briar_rose', 'BRIAR ROSE', 'Grimm - Briar Rose'),
    ('dog_and_the_sparrow', 'THE DOG AND THE SPARROW',
     'Grimm - the Dog And the Sparrow'),
    ('twelve_dancing_princesses', 'THE TWELVE DANCING PRINCESSES',
     'Grimm - the Twelve Dancing Princesses'),
    ('fisherman_and_his_wife', 'THE FISHERMAN AND HIS WIFE',
     'Grimm - the Fisherman And His Wife'),
    ('willow-wren_and_the_bear', 'THE WILLOW-WREN AND THE BEAR',
     'Grimm - the Willow-wren And the Bear'),
    ('frog-prince', 'THE FROG-PRINCE', 'Grimm - the Frog-prince'),
    ('cat_and_mouse_in_partnership', 'CAT AND MOUSE IN PARTNERSHIP',
     'Grimm - Cat And Mouse In Partnership'),
    ('goose-girl', 'THE GOOSE-GIRL', 'Grimm - the Goose-girl'),
    ('adventures_of_chanticleer_and_partlet', 'THE ADVENTURES OF CHANTICLEER AND PARTLET',
     'Grimm - the Adventures Of Chanticleer And Partlet'),
    ('rapunzel', 'RAPUNZEL', 'Grimm - Rapunzel'),
    ('fundevogel', 'FUNDEVOGEL', 'Grimm - Fundevogel'),
    ('valiant_little_tailor', 'THE VALIANT LITTLE TAILOR',
     'Grimm - the Valiant Little Tailor'),
    ('hansel_and_gretel', 'HANSEL AND GRETEL', 'Grimm - Hansel And Gretel'),
    ('mouse,_the_bird,_and_the_sausage', 'THE MOUSE, THE BIRD, AND THE SAUSAGE',
     'Grimm - the Mouse, the Bird, And the Sausage'),
    ('mother_holle', 'MOTHER HOLLE', 'Grimm - Mother Holle'),
    ('little_red-cap_[little_red_riding_hood]', 'LITTLE RED-CAP [LITTLE RED RIDING HOOD]',
     'Grimm - Little Red-cap [little Red Riding Hood]'),
    ('robber_bridegroom', 'THE ROBBER BRIDEGROOM', 'Grimm - the Robber Bridegroom'),
    ('tom_thumb', 'TOM THUMB', 'Grimm - Tom Thumb'),
    ('rumpelstiltskin', 'RUMPELSTILTSKIN', 'Grimm - Rumpelstiltskin'),
    ('clever_gretel', 'CLEVER GRETEL', 'Grimm - Clever Gretel'),
    ('old_man_and_his_grandson', 'THE OLD MAN AND HIS GRANDSON',
     'Grimm - the Old Man And His Grandson'),
    ('little_peasant', 'THE LITTLE PEASANT', 'Grimm - the Little Peasant'),
    ('frederick_and_catherine', 'FREDERICK AND CATHERINE',
     'Grimm - Frederick And Catherine'),
    ('sweetheart_roland', 'SWEETHEART ROLAND', 'Grimm - Sweetheart Roland'),
    ('snowdrop', 'SNOWDROP', 'Grimm - Snowdrop'),
    ('pink', 'THE PINK', 'Grimm - the Pink'),
    ('clever_elsie', 'CLEVER ELSIE', 'Grimm - Clever Elsie'),
    ('miser_in_the_bush', 'THE MISER IN THE BUSH', 'Grimm - the Miser In the Bush'),
    ('ashputtel', 'ASHPUTTEL', 'Grimm - Ashputtel'),
    ('white_snake', 'THE WHITE SNAKE', 'Grimm - the White Snake'),
    ('wolf_and_the_seven_little_kids', 'THE WOLF AND THE SEVEN LITTLE KIDS',
     'Grimm - the Wolf And the Seven Little Kids'),
    ('queen_bee', 'THE QUEEN BEE', 'Grimm - the Queen Bee'),
    ('elves_and_the_shoemaker', 'THE ELVES AND THE SHOEMAKER',
     'Grimm - the Elves And the Shoemaker'),
    ('juniper-tree', 'THE JUNIPER-TREE', 'Grimm - the Juniper-tree'),
    ('turnip', 'THE TURNIP', 'Grimm - the Turnip'),
    ('clever_hans', 'CLEVER HANS', 'Grimm - Clever Hans'),
    ('three_languages', 'THE THREE LANGUAGES', 'Grimm - the Three Languages'),
    ('fox_and_the_cat', 'THE FOX AND THE CAT', 'Grimm - the Fox And the Cat'),
    ('four_clever_brothers', 'THE FOUR CLEVER BROTHERS',
     'Grimm - the Four Clever Brothers'),
    ('lily_and_the_lion', 'LILY AND THE LION', 'Grimm - Lily And the Lion'),
    ('fox_and_the_horse', 'THE FOX AND THE HORSE', 'Grimm - the Fox And the Horse'),
    ('blue_light', 'THE BLUE LIGHT', 'Grimm - the Blue Light'),
    ('raven', 'THE RAVEN', 'Grimm - the Raven'),
    ('golden_goose', 'THE GOLDEN GOOSE', 'Grimm - the Golden Goose'),
    ('water_of_life', 'THE WATER OF LIFE', 'Grimm - the Water Of Life'),
    ('twelve_huntsmen', 'THE TWELVE HUNTSMEN', 'Grimm - the Twelve Huntsmen'),
    ('king_of_the_golden_mountain', 'THE KING OF THE GOLDEN MOUNTAIN',
     'Grimm - the King Of the Golden Mountain'),
    ('doctor_knowall', 'DOCTOR KNOWALL', 'Grimm - Doctor Knowall'),
    ('seven_ravens', 'THE SEVEN RAVENS', 'Grimm - the Seven Ravens'),
    ('wedding_of_mrs_fox', 'THE WEDDING OF MRS FOX',
     'Grimm - the Wedding Of Mrs Fox'),
    ('salad', 'THE SALAD', 'Grimm - the Salad'),
    ('story_of_the_youth_who_went_forth_to_learn_what_fear_was', 'THE STORY OF THE YOUTH WHO WENT FORTH TO LEARN WHAT FEAR WAS',
     'Grimm - the Story Of the Youth Who Went Forth To Learn What Fear Was'),
    ('king_grisly-beard', 'KING GRISLY-BEARD', 'Grimm - King Grisly-beard'),
    ('iron_hans', 'IRON HANS', 'Grimm - Iron Hans'),
    ('cat-skin', 'CAT-SKIN', 'Grimm - Cat-skin'),
    ('snow-white_and_rose-red', 'SNOW-WHITE AND ROSE-RED',
     'Grimm - Snow-white And Rose-red')
]


def find_paragraphs_grimmfairytales(soup, start_heading_text):
    """Find paragraphs following a specific heading in a BeautifulSoup object."""

    # Find the start heading - this is brittle and may need to be adjusted for different stories
    start_heading = soup.find(
        lambda tag: tag.name in ('h2', 'h3') and start_heading_text in tag.get_text(strip=True))

    if start_heading is None:
        return None

    # If we got the heading, try to return the paragraphs following it
    paragraphs = []
    current_element = start_heading.find_next_sibling()

    # Iterate through sibling elements until the next heading or the end of the siblings is reached.
    while current_element and current_element.name not in ('h2', 'div'):
        if current_element.name == 'p' or current_element.name == 'pre':
            paragraphs.append(re.sub(r'[\xc2-\xf4][\x80-\xbf]+', lambda m: m.group(
                0).encode('latin1').decode('utf8'), current_element.get_text(strip=False)))
        current_element = current_element.find_next_sibling()

    return '\n'.join(paragraphs)


def create_download_callback(story_name, url, start_heading_text, description):
    """Create a download callback function for a specific story."""
    def story_download_callback(contents):
        """Download a specific Grimm story from the Gutenberg Project."""

        if contents is None:
            raise ValueError(f"Failed to download {url}")

        story_soup = BeautifulSoup(contents, "lxml")

        story_text = find_paragraphs_grimmfairytales(
            story_soup, start_heading_text)
        if story_text is None:
            raise ValueError(
                f"Failed to find text for {story_name} given {start_heading_text} in {url}")

        story_data = {
            "author": "Grimm",
            "year": 1812,
            "url": url,
            "name": story_name,
        }

        return description, story_text, story_data

    return story_download_callback


def gather():
    """Run DataGatherers for the Grimm corpus."""
    gatherer = downloaders.DataGatherer(
        TARGET_DIRECTORY,
        description="Grimm stories from the Gutenberg Project.",
        license="Public domain, from Project Gutenberg.")
    for filename, heading, title in GRIMM_HEADINGS:
        gatherer.download(
            filename,
            GRIMM_GUTENBERG,
            create_download_callback(
                story_name=filename,
                url=GRIMM_GUTENBERG,
                start_heading_text=heading,
                description=title))
    return gatherer.downloads


def main():
    """Extract the Grimm stories from the Gutenberg Project."""
    print("Gathering Grimm stories.")
    downloads = gather()
    print(f" - Total stories in Grimm corpus: {len(downloads)}")


if __name__ == "__main__":
    main()
