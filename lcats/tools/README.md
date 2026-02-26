# LCATS Tools

This directory contains scripts and templates designed to facilitate AI-assisted programming workflows. These tools help generate structured requests for AI agents and provide source code analysis for better development understanding.

## Tools Overview

### 1. Source Tree Surveyor (`sourcetree_surveyor.py`)

A Python source analysis tool that inventories public API surface area to help assess testability and plan unit tests.

**Purpose**: Extract the public API surface of Python modules for AI-assisted development, enabling better understanding of what needs testing or coverage improvements.

**Usage:**
```bash
# Generate markdown summary of a source tree
python tools/sourcetree_surveyor.py lcats/lcats/utils --format md

# Generate JSON output for programmatic use
python tools/sourcetree_surveyor.py lcats/lcats/utils --format json

# Include test file analysis (checks if corresponding tests exist)
python tools/sourcetree_surveyor.py lcats/lcats/utils --tests-root lcats/tests/utils_tests --format md
```

**Features:**
- Identifies public functions, classes, and methods in Python files
- Marks private symbols (starting with `_` or `__`)
- Extracts docstring summaries
- Counts top-level imports
- Detects main guard patterns
- Suggests test file paths and checks for existing tests
- Outputs in markdown or JSON format

**Output includes:**
- Module-level information (imports, main guard)
- Function inventory with line numbers and privacy status
- Class inventory with methods
- Test coverage suggestions

### 2. PR Request Generator (`create_request.py`)

A template-driven tool that generates structured Pull Request descriptions with computed variables for AI-assisted development workflows.

**Purpose**: Create standardized, detailed PR requests that provide AI agents with comprehensive context and instructions for specific development tasks.

**Usage:**
```bash
# Generate a coverage improvement request
python tools/create_request.py improve_coverage lcats/analysis/llm_extractor.py

# Show computed variables for debugging
python tools/create_request.py improve_coverage lcats/analysis/llm_extractor.py --show-vars
```

**Features:**
- Template-based PR request generation
- Automatic path normalization for repository structure
- Variable substitution with computed values
- Support for multiple input path formats

**Computed Variables:**
- `{{TEMPLATE_NAME}}` - The template being used
- `{{TARGET_INPUT}}` - Original path input provided
- `{{TARGET_MODULE_GHA}}` - Normalized GitHub Actions compatible path
- `{{MODULE_NAME}}` - Base module name
- `{{SUGGESTED_TEST_PATH}}` - Computed test file path following project conventions

## Templates

### Coverage Improvement Template (`templates/improve_coverage.md`)

A comprehensive template for requesting AI assistance in improving test coverage for specific modules.

**Features:**
- **Environment Bootstrap**: Step-by-step setup instructions
- **Strict Constraints**: Clear boundaries (test-only changes, specific imports, etc.)
- **Output Handling**: Guidelines for managing debug prints and user-facing output
- **Required Process**: 9-step workflow from coverage analysis to final validation
- **Failure Policy**: Clear guidance on how to handle common issues
- **Acceptance Criteria**: Specific requirements for successful completion

**Key Principles:**
- Only modify test files, never production code
- Use existing test utilities for output capture/suppression
- Follow deterministic testing practices
- Maintain formatting and linting standards
- Provide clear before/after metrics

## AI-Assisted Development Workflow

These tools support a structured approach to AI-assisted programming:

1. **Analysis Phase**: Use `sourcetree_surveyor.py` to understand API surface area
2. **Request Generation**: Use `create_request.py` with appropriate templates
3. **AI Interaction**: Provide the generated request to AI agents
4. **Validation**: Follow template guidelines for quality assurance

## Adding New Templates

To create new templates:

1. Create a new `.md` file in `tools/templates/`
2. Use `{{VARIABLE_NAME}}` syntax for interpolation
3. Available variables are computed in `create_request.py`
4. Test with `--show-vars` flag to verify variable substitution

## Path Conventions

The tools understand LCATS project structure:

- **Input**: `analysis/foo.py` or `lcats/analysis/foo.py` 
- **Normalized**: `lcats/lcats/analysis/foo.py`
- **Test Path**: `lcats/tests/analysis_tests/foo_test.py`

This automatic path normalization ensures consistency across different working directories and input formats.

## Integration with AI Agents

These tools are designed to work with AI coding assistants by:

- Providing comprehensive, structured instructions
- Including environmental context and constraints
- Offering clear success/failure criteria
- Automating path computation and template variable substitution
- Supporting reproducible development workflows

The generated requests can be pasted directly into AI chat sessions to provide detailed context for complex development tasks.