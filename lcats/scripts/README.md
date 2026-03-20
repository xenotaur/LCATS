# LCATS Development Scripts

This directory contains utility scripts for development, testing, and maintenance of the LCATS package. All scripts are designed to be executed from the `lcats` directory of the LCATS project,
which is parallel to the `corpora` and `experiments` directories and contains all actual code.

## Usage

Execute any script from the `lcats` directory under the project root:
```bash
scripts/<script_name>
```

## Available Scripts

### Build & Distribution

#### `build`
Builds the LCATS package using Python's build module.

```bash
scripts/build
```

**Requirements:**
- `pip install build`

**Output:** Creates distribution files in `dist/` directory.

#### `clean`
Removes all build artifacts to ensure a clean state.

```bash
scripts/clean
```

**Removes:**
- `build/` directory
- `dist/` directory  
- `lcats.egg-info/` directory

#### `publish`
Publishes the LCATS package to PyPI using twine.

```bash
scripts/publish
```

**Requirements:**
- `pip install twine`
- Must run `scripts/build` first

**Note:** Currently disabled for safety until LCATS is more thoroughly tested.

### Development

#### `develop`
Installs LCATS in development mode for active development.

```bash
scripts/develop
```

This installs the package with `pip install -e .`, allowing you to make changes to the source code that are immediately reflected without reinstalling.

#### `update`
Updates the conda environment specification file.

```bash
scripts/update
```

**Output:** Updates `environment.yml` with current conda environment dependencies (excludes name and prefix).

### Code Quality

#### `format`
Formats Python code using Black formatter.

```bash
scripts/format
```

**Applies formatting to:**
- `lcats/` directory
- `tests/` directory

#### `lint`
Lints Python code using Ruff linter.

```bash
scripts/lint [additional-ruff-args]
```

**Checks:**
- `lcats/` directory
- `tests/` directory

**Additional arguments:** Pass any additional ruff arguments after the script name.

### Testing

#### `test`
Runs the test suite using Python's `unittest` framework.

```bash
scripts/test [target]
```

**Default behavior (no arguments):**
- Discovers and runs all tests in the `tests/` directory
- Matches files with pattern `*_test.py`

```bash
scripts/test
```

**Targeted test execution:**

The `test` script also supports running a subset of tests by passing a target. The target can be:

- A **directory**
- A **test file**
- A **dotted module path**
- A **specific test class or method**

**Examples:**

_Run all tests in a subdirectory:_
```bash
scripts/test tests/gatherers
```

_Run a single test file:_
```bash
scripts/test tests/gatherers/downloaders_test.py
```

_Run a module (dotted path):_
```bash
scripts/test tests.gatherers.downloaders_test
```

_Run a specific test class:_
```bash
scripts/test tests.gatherers.downloaders_test.TestDownloader
```

_Run a single test method:_
```bash
scripts/test tests.gatherers.downloaders_test.TestDownloader.test_detect_encoding
```

**Test Discovery:**
- Directory targets use `unittest discover` under the specified path.
- File paths are automatically converted to module paths.
- Dotted paths provide the most precise and reliable way to target individual tests.
- If no target is provided, full test discovery is used.


#### `coverage`
Runs test coverage analysis and generates reports.

```bash
scripts/coverage [--html]
```

**Options:**
- No arguments: Displays coverage report in terminal with missing lines
- `--html`: Generates HTML coverage report in `htmlcov/index.html`

**Process:**
1. Erases previous coverage data
2. Runs tests with coverage tracking
3. Generates coverage report

## Development Workflow

### Initial Setup
```bash
scripts/develop    # Install in development mode
```

### Regular Development
```bash
scripts/format     # Format code
scripts/lint       # Check for issues
scripts/test       # Run tests
scripts/coverage   # Check coverage
```

### Build & Release Workflow
```bash
scripts/clean      # Clean previous builds
scripts/build      # Build distribution
scripts/publish    # Publish to PyPI (when enabled)
```

### Environment Management
```bash
scripts/update     # Update environment.yml when dependencies change
```

## Notes

- All scripts assume execution from the LCATS/lcats software directory
- Scripts use `set -x` for verbose output during execution
- Scripts with `set -euo pipefail` will exit on any error
- The publish script is currently disabled as a safety measure during development

## Dependencies

Make sure you have the following tools installed for full functionality:

- **Build:** `pip install build`
- **Publish:** `pip install twine` 
- **Format:** `pip install black`
- **Lint:** `pip install ruff`
- **Coverage:** `pip install coverage`
- **Environment:** conda (for environment export)