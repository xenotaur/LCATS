# LCATS - Literary Captain's Advisory Tool System

LCATS (Literary Captain's Advisory Tool System) is a comprehensive toolkit for creating, managing, and analyzing text corpora using large language models. This system combines traditional text processing techniques with modern LLM capabilities to enable sophisticated literary analysis, story extraction, and corpus-based research.

## Overview

LCATS consists of several key components:

- **`lcats` Python Package**: Core library for text corpus creation and analysis
- **Story Corpora**: Curated collection of public domain literature in JSON format  
- **Analysis Tools**: Text chunking, extraction, and story analysis capabilities
- **Data Gatherers**: Automated collection from sources like Project Gutenberg
- **Processing Pipeline**: Flexible stage-based processing framework
- **Command-Line Interface**: Easy-to-use CLI for common operations

## Features

### 📚 Story Corpus Management
- Load and manage collections of stories from multiple authors/genres
- Structured JSON format with metadata (author, year, URL, etc.)
- Support for various literary sources and formats

### 🔍 Text Analysis & Processing
- **Chunking**: Token-aware text segmentation using tiktoken
- **Extraction**: LLM-powered structured data extraction from stories
- **Analysis**: Keyword extraction, text statistics, and story metrics
- **Pipeline**: Configurable multi-stage processing workflows

### 🤖 LLM Integration
- OpenAI API integration for text analysis and extraction
- Template-based prompt engineering for consistent results
- Structured output parsing and error handling
- Configurable models and parameters

### 🔄 Data Collection
- Automated gathering from Project Gutenberg and other sources
- Specialized gatherers for different authors and collections
- Consistent formatting and metadata extraction

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/xenotaur/LCATS.git
cd LCATS/lcats

# Install in development mode
scripts/clean && scripts/build && scripts/develop

# Verify installation
lcats info
```

### Basic Usage

```bash
# Get help
lcats help

# Gather corpus data
lcats gather

# Inspect a story
lcats inspect ../corpora/anderson/bell.json
```

### Python API

```python
from lcats.stories import Corpora, Story
from lcats.chunking import chunk_story
from lcats.extraction import extract_from_story, ExtractionTemplate

# Load a corpus
corpus = Corpora("../corpora")
stories = corpus.stories

# Work with individual stories
story = Story.from_json_file("path/to/story.json")

# Chunk long texts
chunks = chunk_story(story.body, max_tokens=1000)

# Extract structured data with LLM
template = ExtractionTemplate(
    name="events",
    system_template="Extract story events as JSON",
    user_template="Story: {story_text}"
)
result = extract_from_story(story.body, template, client)
```

## Project Structure

```
LCATS/
├── README.md                 # This file
├── lcats/                    # Python package
│   ├── lcats/               # Core library code
│   │   ├── stories.py       # Story and corpus classes
│   │   ├── pipeline.py      # Processing pipeline framework
│   │   ├── chunking.py      # Text chunking utilities  
│   │   ├── extraction.py    # LLM-based data extraction
│   │   ├── analysis/        # Text analysis tools
│   │   ├── gatherers/       # Data collection modules
│   │   └── cli.py          # Command-line interface
│   ├── scripts/            # Development utilities
│   ├── tests/              # Unit tests
│   └── tools/              # Development tools
├── corpora/                 # Story collections
│   ├── anderson/           # Hans Christian Andersen
│   ├── grimm/             # Brothers Grimm
│   ├── sherlock/          # Arthur Conan Doyle
│   ├── lovecraft/         # H.P. Lovecraft
│   └── ...               # Additional authors
├── experiments/           # Research experiments
└── Papers/               # Academic references
```

## Corpora

LCATS includes a substantial collection of public domain literature:

### Authors & Collections
- **Hans Christian Andersen**: Classic fairy tales and stories
- **Brothers Grimm**: Traditional German folk tales  
- **Arthur Conan Doyle**: Sherlock Holmes stories
- **G.K. Chesterton**: Father Brown detective stories
- **H.P. Lovecraft**: Cosmic horror fiction
- **O. Henry**: Short stories with twist endings
- **Oscar Wilde**: Literary works including "The Happy Prince"
- **Jack London**: Adventure and naturalist fiction
- **Ernest Hemingway**: Modernist short stories
- **P.G. Wodehouse**: Humorous fiction

### Story Format
Each story is stored as JSON with consistent structure:

```json
{
    "name": "Story Title",
    "body": "Full text of the story...",
    "metadata": {
        "author": "Author Name",
        "year": 1911,
        "url": "https://www.gutenberg.org/...",
        "name": "filename_slug"
    }
}
```

## Development

### Requirements
- Python 3.6+
- Dependencies listed in `pyproject.toml`
- OpenAI API key (for LLM features)

### Development Setup

```bash
cd LCATS/lcats

# Install development dependencies
pip install -e ".[dev]"

# Run tests
scripts/test

# Run linting and formatting  
scripts/lint
scripts/format

# Generate coverage report
scripts/coverage
```

### Available Scripts

| Script | Purpose |
|--------|---------|
| `scripts/build` | Build distribution packages |
| `scripts/clean` | Remove build artifacts |
| `scripts/test` | Run unit tests |
| `scripts/coverage` | Generate coverage reports |
| `scripts/lint` | Run code linting |
| `scripts/format` | Format code with black |
| `scripts/develop` | Install in development mode |

## CLI Commands

| Command | Description |
|---------|-------------|
| `lcats help` | Show usage information |
| `lcats info` | Display system information |
| `lcats gather [gatherers]` | Collect corpus data |
| `lcats inspect <file>` | Examine story JSON files |
| `lcats index` | Preprocess corpus (planned) |
| `lcats advise` | AI advisory interface (planned) |
| `lcats eval` | Benchmark evaluation (planned) |

## API Reference

### Core Classes

- **`Story`**: Individual story with text, metadata, and loading methods
- **`Corpora`**: Collection manager for multiple story corpora
- **`Pipeline`**: Configurable multi-stage processing framework
- **`ExtractionTemplate`**: Template for LLM-based data extraction
- **`Chunk`**: Text segment with token and character offsets

### Key Modules

- **`lcats.stories`**: Story and corpus management
- **`lcats.pipeline`**: Processing pipeline framework  
- **`lcats.chunking`**: Text segmentation utilities
- **`lcats.extraction`**: LLM-based extraction tools
- **`lcats.analysis`**: Text analysis and metrics
- **`lcats.gatherers`**: Data collection modules

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run `scripts/test` and `scripts/lint`
5. Submit a pull request

## License

LCATS is released under the MIT License. The story corpora are public domain works.

## Academic Use

LCATS was developed to support research in computational narrative analysis, story understanding, and case-based reasoning with large language models. If you use LCATS in academic work, please cite this repository.

## Support

For questions, issues, or contributions, please use the GitHub issue tracker or contact the maintainers.
