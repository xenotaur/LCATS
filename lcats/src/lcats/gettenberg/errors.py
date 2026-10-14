"""Structured failures for the LCATS-owned Gutenberg metadata interfaces."""


class GettenbergError(Exception):
    """Base class for operational gettenberg failures."""


class RecordParseError(GettenbergError, ValueError):
    """An input cannot be represented by the supported Gutenberg RDF profile.

    Attributes:
        code: Stable machine-readable failure category.
        source_name: Caller-supplied evidence label, never opened by the parser.
    """

    def __init__(self, code: str, source_name: str, message: str):
        self.code = code
        self.source_name = source_name
        super().__init__(f"{source_name}: {code}: {message}")


class ExportLimitError(GettenbergError, ValueError):
    """A complete JSON-compatible export would exceed its explicit budgets."""
