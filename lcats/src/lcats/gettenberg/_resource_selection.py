"""Pure selection from declared formats; never infer routes or inspect bytes."""

import codecs
import dataclasses
import re

from lcats.gettenberg import _resource_types
from lcats.gettenberg import models

# Parse only the validated MIME subset. General email parsers normalize RFC 2231
# continuations, which can turn malformed metadata into a misleading charset.
_TOKEN = r"[!#$%&'*+.^_`|~0-9A-Za-z-]+"
_MEDIA = re.compile(rf"{_TOKEN}/{_TOKEN}")
_VALUE = rf"""(?:{_TOKEN}|"(?:[^"\\\r\n]|\\[^\r\n])*")"""
_PARAMETER = re.compile(rf"\s*;\s*({_TOKEN})\s*=\s*({_VALUE})")
_CLAIM = re.compile(rf"{_TOKEN}/{_TOKEN}(?:{_PARAMETER.pattern})*\s*")


def _charset(value: str) -> str:
    """Normalize known codec aliases without guessing an unknown encoding."""
    try:
        return codecs.lookup(value).name
    except LookupError:
        return value.casefold()


@dataclasses.dataclass(frozen=True, slots=True)
class ResourcePreference:
    """Exact media type and optional charset; None accepts any declared charset.

    Media types are case-insensitive, without parameters or wildcards. Charset
    aliases known to Python normalize equally; unknown names compare literally
    ignoring case. A preference expresses selection, never decoder support.
    """

    media_type: str
    charset: str | None = None

    def __post_init__(self):
        if not isinstance(self.media_type, str) or not _MEDIA.fullmatch(
            self.media_type
        ):
            raise _resource_types.ResourceInputError(
                "invalid_preference", "use an exact type/subtype without parameters"
            )
        if "*" in self.media_type:
            raise _resource_types.ResourceInputError(
                "invalid_preference", "wildcard media preferences are unsupported"
            )
        object.__setattr__(self, "media_type", self.media_type.lower())
        if self.charset is not None:
            if not isinstance(self.charset, str) or not re.fullmatch(
                _TOKEN, self.charset
            ):
                raise _resource_types.ResourceInputError(
                    "invalid_preference", "charset must be a nonempty MIME token"
                )
            object.__setattr__(self, "charset", _charset(self.charset))


@dataclasses.dataclass(frozen=True, slots=True)
class SelectionDiagnostic:
    """A stable code and explanation, with zero-based source positions if known."""

    code: str
    message: str
    resource_index: int | None = None
    format_index: int | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class ResourceSelection:
    """Selected original metadata plus the exact claim and preference that won.

    A no-match result has all four selection fields None. Diagnostics describe
    malformed claims, unmatched resources and ties; the ebook is never modified.
    """

    resource: models.Resource | None
    source_index: int | None
    preference_index: int | None
    matched_format: str | None
    diagnostics: tuple[SelectionDiagnostic, ...]
    policy_version: str = "declared-media-v1"


DEFAULT_PREFERENCES = (
    ResourcePreference("text/plain", "utf-8"),
    ResourcePreference("text/plain"),
    ResourcePreference("text/html"),
)


def select_resource(
    ebook: models.Ebook,
    *,
    preferences: tuple[ResourcePreference, ...] = DEFAULT_PREFERENCES,
) -> ResourceSelection:
    """Select by ordered preferences, then source resource and format order.

    Args:
        ebook: Metadata whose resources and format claims retain source order.
        preferences: Nonempty immutable tuple of exact media/optional charset
            preferences. Defaults to UTF-8 plain text, other plain text, HTML.

    Returns:
        Immutable selection, or a no-match result with diagnostic code no_match.
        Unsupported extraction formats remain selectable with explicit preferences.

    Raises:
        ResourceInputError: Ebook or preference arguments have the wrong shape.
    """
    if (
        not isinstance(ebook, models.Ebook)
        or not isinstance(preferences, tuple)
        or not preferences
        or any(not isinstance(p, ResourcePreference) for p in preferences)
    ):
        raise _resource_types.ResourceInputError(
            "invalid_selection", "use Ebook and a nonempty tuple of ResourcePreference"
        )
    diagnostics = []
    candidates = []
    for resource_index, resource in enumerate(ebook.resources):
        matches = []
        for format_index, term in enumerate(resource.formats):
            claim = term.value.text
            if not _CLAIM.fullmatch(claim.strip()) or any(
                ord(char) < 32 and char != "\t" or ord(char) >= 127 for char in claim
            ):
                diagnostics.append(
                    SelectionDiagnostic(
                        "invalid_format",
                        "Malformed media claim ignored",
                        resource_index,
                        format_index,
                    )
                )
                continue
            media_type = claim.split(";", 1)[0].strip().lower()
            parameters = []
            extended_charset = False
            for parameter in _PARAMETER.finditer(claim):
                name, value = parameter.groups()
                name = name.lower()
                if name.startswith("charset*"):
                    extended_charset = True
                if value.startswith('"'):
                    value = re.sub(r"\\(.)", r"\1", value[1:-1])
                parameters.append((name, value))
            # Duplicate charset declarations must agree before a charset-specific
            # preference can match. A generic media preference can still select it;
            # a later decoder must independently resolve encoding evidence.
            charset_values = [value for name, value in parameters if name == "charset"]
            if extended_charset or any(
                not re.fullmatch(_TOKEN, value) for value in charset_values
            ):
                diagnostics.append(
                    SelectionDiagnostic(
                        "invalid_format",
                        "Invalid or extended charset parameter ignored",
                        resource_index,
                        format_index,
                    )
                )
                continue
            charsets = {_charset(value) for value in charset_values}
            if len(charsets) > 1:
                diagnostics.append(
                    SelectionDiagnostic(
                        "conflicting_charsets",
                        "Charset-specific match refused",
                        resource_index,
                        format_index,
                    )
                )
            charset = next(iter(charsets)) if len(charsets) == 1 else None
            for preference_index, preference in enumerate(preferences):
                if media_type == preference.media_type and (
                    preference.charset is None or preference.charset == charset
                ):
                    matches.append(
                        (preference_index, resource_index, format_index, claim)
                    )
                    break
        if matches:
            candidates.append(min(matches))
        else:
            diagnostics.append(
                SelectionDiagnostic(
                    "unmatched_resource",
                    "No declared format matches preferences",
                    resource_index,
                )
            )
    if not candidates:
        diagnostics.append(SelectionDiagnostic("no_match", "No matching resource"))
        return ResourceSelection(None, None, None, None, tuple(diagnostics))
    preference_index, resource_index, _, claim = min(candidates)
    if sum(candidate[0] == preference_index for candidate in candidates) > 1:
        diagnostics.append(
            SelectionDiagnostic(
                "source_order_tie",
                "Equal preference resolved by resource source order",
                resource_index,
            )
        )
    return ResourceSelection(
        ebook.resources[resource_index],
        resource_index,
        preference_index,
        claim,
        tuple(diagnostics),
    )
