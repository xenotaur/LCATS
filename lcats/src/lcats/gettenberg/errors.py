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


class CatalogError(GettenbergError):
    """A local catalog operation failed."""


class CatalogMissingError(CatalogError, FileNotFoundError):
    """The explicitly requested catalog does not exist."""


class CatalogSchemaError(CatalogError):
    """The catalog schema, parser version or stored evidence is incompatible."""


class CatalogIncompleteError(CatalogError):
    """The candidate did not complete ingestion and integrity qualification."""


class CatalogClosedError(CatalogError):
    """A query was attempted after closing its catalog session."""


class CatalogInputError(CatalogError, ValueError):
    """An ID, query, pagination argument or catalog limit is invalid."""


class CatalogBuildError(CatalogError):
    """A candidate build failed; report describes the incomplete output.

    Attributes:
        code: Machine-readable failure category.
        report: Final BuildReport, or None if no candidate was created.
    """

    def __init__(self, code, message, report=None):
        self.code = code
        self.report = report
        super().__init__(f"{code}: {message}")
