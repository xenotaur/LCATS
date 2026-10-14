"""Pure, bounded parser for the observed Project Gutenberg RDF/XML profile.

This is intentionally not a general RDF graph engine. Known properties with
unsupported shapes fail explicitly; unknown predicates remain in original
source evidence and produce diagnostics. Nothing opens a path or URL.
"""

import functools
import hashlib
import re
from urllib import parse

from lxml import etree

from lcats.gettenberg import errors
from lcats.gettenberg import models

RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
PG = "http://www.gutenberg.org/2009/pgterms/"
DC = "http://purl.org/dc/terms/"
DCAM = "http://purl.org/dc/dcam/"
RELATORS = "http://id.loc.gov/vocabulary/relators/"
XML = "http://www.w3.org/XML/1998/namespace"
CC = "http://web.resource.org/cc/"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
DEFAULT_MAX_BYTES = 2 * 1024**2
_WHITESPACE = re.compile(r"\s")


@functools.lru_cache(maxsize=64)
def _tag(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"


def _predicate(tag: str) -> str:
    name = etree.QName(tag)
    return (name.namespace or "") + name.localname


def parse_record(
    data: bytes, *, source_name: str, max_bytes: int = DEFAULT_MAX_BYTES
) -> models.ParsedRecord:
    """Parse one bounded, self-contained Gutenberg ebook RDF record.

    Args:
        data: Original XML bytes; never a filename or URL.
        source_name: Nonempty evidence label, such as an archive member name.
        max_bytes: Positive input limit, checked before XML parsing (2 MiB).

    Returns:
        Immutable ebook, exact source bytes/hash, and unmodeled diagnostics.

    Raises:
        TypeError: Arguments have incorrect types.
        ValueError: The label is empty or the limit is not positive.
        errors.RecordParseError: Oversized/unsafe/malformed XML, invalid
            identity/value, or an unsupported known RDF shape.
    """
    if not isinstance(data, bytes):
        raise TypeError("data must be bytes, not a path, URL or decoded string")
    if not isinstance(source_name, str):
        raise TypeError("source_name must be a string")
    if not source_name.strip():
        raise ValueError("source_name must be a nonempty string")
    if type(max_bytes) is not int or max_bytes <= 0:
        raise ValueError("max_bytes must be a positive integer")
    if len(data) > max_bytes:
        raise errors.RecordParseError("record_too_large", source_name, str(max_bytes))
    parser = etree.XMLParser(
        resolve_entities=False,
        load_dtd=False,
        no_network=True,
        huge_tree=False,
        recover=False,
    )
    try:
        root = etree.fromstring(data, parser=parser)
    except etree.XMLSyntaxError as exc:
        raise errors.RecordParseError("malformed_xml", source_name, str(exc)) from exc
    if root.getroottree().docinfo.doctype:
        raise errors.RecordParseError("unsafe_xml", source_name, "DOCTYPE is forbidden")
    reader = _Reader(root, source_name)
    ebook = reader.ebook()
    return models.ParsedRecord(
        ebook=ebook,
        source=models.SourceEvidence(
            source_name, hashlib.sha256(data).hexdigest(), data
        ),
        diagnostics=reader.diagnostics(),
    )


class _Reader:
    """One record's parsing state; discarded before returning public records."""

    def __init__(self, root, source_name):
        self.root = root
        self.source_name = source_name
        self.consumed = set()
        self.notices = []
        self.agent_nodes = {}
        self.resolved_uris = {}

    def fail(self, code, message):
        raise errors.RecordParseError(code, self.source_name, message)

    def children(self, parent, namespace, name):
        found = parent.findall(_tag(namespace, name))
        self.consumed.update(found)
        return found

    def elements(self, parent):
        return [child for child in parent if isinstance(child.tag, str)]

    def literal(self, node):
        if self.elements(node) or node.get(_tag(RDF, "resource")) is not None:
            self.fail("unsupported_shape", f"expected a literal: {node.tag}")
        language = None
        for ancestor in (node, *node.iterancestors()):
            if _tag(XML, "lang") in ancestor.attrib:
                language = ancestor.get(_tag(XML, "lang")) or None
                break
        datatype = node.get(_tag(RDF, "datatype"))
        if datatype is not None:
            datatype = self.resolve(node, datatype)
        return models.Literal(node.text or "", language, datatype)

    def literals(self, parent, namespace, name):
        return tuple(self.literal(n) for n in self.children(parent, namespace, name))

    def resolve(self, node, value):
        key = (node, value)
        if key in self.resolved_uris:
            return self.resolved_uris[key]
        normalized = _WHITESPACE.sub(
            lambda match: parse.quote(match.group(), safe=""), value
        )
        if normalized != value:
            self.notices.append(
                models.Diagnostic(
                    "normalized_uri",
                    self.root.getroottree().getpath(node),
                    _predicate(node.tag),
                    f"Percent-encoded source URI whitespace: {value!r} -> {normalized!r}",
                )
            )
        try:
            uri = parse.urljoin(node.base or "", normalized)
            scheme = parse.urlsplit(uri).scheme
        except ValueError as exc:
            self.fail("invalid_identity", f"invalid URI: {exc}")
        if not scheme or _WHITESPACE.search(uri):
            self.fail("invalid_identity", f"unresolved or invalid URI: {value!r}")
        self.resolved_uris[key] = uri
        return uri

    def uri(self, node, attribute):
        value = node.get(_tag(RDF, attribute))
        if value is None:
            self.fail("unsupported_shape", f"missing rdf:{attribute}: {node.tag}")
        return self.resolve(node, value)

    def links(self, parent, namespace, name):
        result = []
        for node in self.children(parent, namespace, name):
            if self.elements(node) or (node.text or "").strip():
                self.fail("unsupported_shape", f"expected URI property: {node.tag}")
            result.append(self.uri(node, "resource"))
        return tuple(result)

    def terms(self, parent, namespace, name):
        result = []
        for prop in self.children(parent, namespace, name):
            descriptions = self.children(prop, RDF, "Description")
            if len(descriptions) != 1 or len(self.elements(prop)) != 1:
                self.fail(
                    "unsupported_shape", f"expected inline rdf:Description: {prop.tag}"
                )
            description = descriptions[0]
            schemes = self.links(description, DCAM, "memberOf")
            values = self.literals(description, RDF, "value")
            if not values:
                self.fail("unsupported_shape", f"missing rdf:value: {prop.tag}")
            result.extend(models.Term(value, schemes) for value in values)
        return tuple(result)

    def integers(self, parent, namespace, name):
        result = []
        for literal in self.literals(parent, namespace, name):
            text = literal.text.strip()
            if not re.fullmatch(r"\+?[0-9]{1,19}", text) or int(text) > 2**63 - 1:
                self.fail(
                    "invalid_value", f"expected nonnegative 64-bit integer: {name}"
                )
            result.append(int(text))
        return tuple(result)

    def agent(self, node):
        self.consumed.add(node)
        return models.Agent(
            uri=self.uri(node, "about"),
            names=self.literals(node, PG, "name"),
            aliases=self.literals(node, PG, "alias"),
            birth_dates=self.literals(node, PG, "birthdate"),
            death_dates=self.literals(node, PG, "deathdate"),
            webpages=self.links(node, PG, "webpage"),
        )

    def contributions(self, ebook):
        result = []
        for prop in self.elements(ebook):
            if prop.tag != _tag(DC, "creator") and not prop.tag.startswith(
                "{" + RELATORS + "}"
            ):
                continue
            self.consumed.add(prop)
            if prop.get(_tag(RDF, "resource")) is not None:
                if self.elements(prop) or (prop.text or "").strip():
                    self.fail(
                        "unsupported_shape", "mixed contributor link and inline value"
                    )
                uri = self.uri(prop, "resource")
                definitions = self.agent_nodes.get(uri, ())
                if not definitions:
                    self.fail(
                        "unsupported_shape",
                        f"agent reference has no in-record definition: {uri}",
                    )
                agents = tuple(self.agent(node) for node in definitions)
                if any(agent != agents[0] for agent in agents[1:]):
                    self.fail(
                        "invalid_identity", f"conflicting agent definitions: {uri}"
                    )
                result.append(models.Contribution(_predicate(prop.tag), agents[0]))
                continue
            agents = self.children(prop, PG, "agent")
            if not agents or len(agents) != len(self.elements(prop)):
                self.fail(
                    "unsupported_shape", f"expected inline pgterms:agent: {prop.tag}"
                )
            result.extend(
                models.Contribution(_predicate(prop.tag), self.agent(a)) for a in agents
            )
        return tuple(result)

    def resources(self, ebook):
        result = []
        for prop in self.children(ebook, DC, "hasFormat"):
            files = self.children(prop, PG, "file")
            if not files or len(files) != len(self.elements(prop)):
                self.fail("unsupported_shape", "expected inline pgterms:file")
            for node in files:
                result.append(
                    models.Resource(
                        uri=self.uri(node, "about"),
                        formats=self.terms(node, DC, "format"),
                        sizes=self.integers(node, DC, "extent"),
                        modified=self.literals(node, DC, "modified"),
                        is_format_of=self.links(node, DC, "isFormatOf"),
                    )
                )
        return tuple(result)

    def ebook(self):
        if self.root.tag != _tag(RDF, "RDF"):
            self.fail("unsupported_record", "expected rdf:RDF root")
        self.consumed.add(self.root)
        for node in self.root.iter():
            if not isinstance(node.tag, str):
                continue
            if any(
                node.get(_tag(RDF, attr)) is not None for attr in ("parseType", "ID")
            ):
                self.fail(
                    "unsupported_shape",
                    "rdf:parseType/rdf:ID graph forms are unsupported",
                )
            if (
                node.get(_tag(RDF, "about")) is not None
                and node.get(_tag(RDF, "nodeID")) is not None
            ):
                self.fail("invalid_identity", "both rdf:about and rdf:nodeID supplied")
        for node in self.root.iter(_tag(PG, "agent")):
            uri = self.uri(node, "about")
            self.agent_nodes.setdefault(uri, []).append(node)
        books = self.children(self.root, PG, "ebook")
        if len(books) != 1 or len(list(self.root.iter(_tag(PG, "ebook")))) != 1:
            self.fail("unsupported_record", "expected exactly one direct pgterms:ebook")
        book = books[0]
        uri = self.uri(book, "about")
        match = re.fullmatch(
            r"https?://www\.gutenberg\.org/ebooks/([1-9][0-9]{0,17})", uri
        )
        if match is None:
            self.fail("invalid_identity", f"invalid Gutenberg ebook URI: {uri!r}")
        titles = []
        additional = []
        for prop in self.elements(book):
            if prop.tag in (_tag(DC, "title"), _tag(DC, "alternative")):
                self.consumed.add(prop)
                titles.append(
                    models.Title(
                        self.literal(prop),
                        "primary" if prop.tag == _tag(DC, "title") else "alternative",
                    )
                )
            if re.fullmatch(r"\{" + re.escape(PG) + r"\}marc[0-9]{3}", prop.tag):
                self.consumed.add(prop)
                additional.append(
                    models.MetadataValue(_predicate(prop.tag), self.literal(prop))
                )
        downloads = self.integers(book, PG, "downloads")
        if len(downloads) > 1:
            self.fail("unsupported_shape", "ambiguous repeated download count")
        # Recognized catalog licensing/comments and linked-page descriptions
        # remain source evidence; do not confuse them with ebook rights.
        for work in self.children(self.root, CC, "Work"):
            self.links(work, CC, "license")
            self.literals(work, RDFS, "comment")
        for description in self.children(self.root, RDF, "Description"):
            self.literals(description, DC, "description")
        return models.Ebook(
            gutenberg_id=int(match.group(1)),
            uri=uri,
            titles=tuple(titles),
            contributors=self.contributions(book),
            languages=self.terms(book, DC, "language"),
            subjects=self.terms(book, DC, "subject"),
            shelves=self.terms(book, PG, "bookshelf"),
            types=self.terms(book, DC, "type"),
            resources=self.resources(book),
            publishers=self.literals(book, DC, "publisher"),
            rights=self.literals(book, DC, "rights"),
            issued=self.literals(book, DC, "issued"),
            descriptions=self.literals(book, DC, "description"),
            contents=self.literals(book, DC, "tableOfContents"),
            licenses=self.links(book, DC, "license"),
            downloads=downloads[0] if downloads else None,
            additional_metadata=tuple(additional),
        )

    def diagnostics(self):
        result = list(self.notices)
        allowed_attributes = {
            _tag(RDF, name) for name in ("about", "resource", "nodeID", "datatype")
        } | {_tag(XML, "base"), _tag(XML, "lang")}
        tree = self.root.getroottree()
        for node in self.root.iter():
            if not isinstance(node.tag, str):
                continue
            if node not in self.consumed:
                result.append(
                    models.Diagnostic(
                        "unmodeled_predicate",
                        tree.getpath(node),
                        _predicate(node.tag),
                        "Preserved in original RDF; not mapped to a typed field.",
                    )
                )
            for attribute in node.attrib:
                if attribute not in allowed_attributes:
                    result.append(
                        models.Diagnostic(
                            "unmodeled_attribute",
                            tree.getpath(node),
                            _predicate(attribute),
                            "Preserved in original RDF; attribute is not modeled.",
                        )
                    )
        return tuple(result)
