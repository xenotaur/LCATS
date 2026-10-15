"""Bounded gzip and ZIP reading without extraction or recursive decoding."""

import io
import pathlib
import stat
import struct
import zipfile
import zlib

from lcats.gettenberg import _decode_types

_TEXT_SUFFIXES = {
    ".txt": "text/plain",
    ".html": "text/html",
    ".htm": "text/html",
    ".xhtml": "application/xhtml+xml",
}


def _inflate(data, limit, window):
    """Inflate exactly one stream, bounding output before allocation grows."""
    decoder = zlib.decompressobj(window)
    output = bytearray()
    try:
        for offset in range(0, len(data), 65536):
            chunk = data[offset : offset + 65536]
            while chunk:
                block = decoder.decompress(chunk, min(65536, limit + 1 - len(output)))
                output.extend(block)
                if len(output) > limit:
                    raise _decode_types.ResourceDecodeError(
                        "decoded_limit", "inflated output exceeds byte limit"
                    )
                if decoder.unused_data:
                    raise _decode_types.ResourceDecodeError(
                        "container_chain",
                        "concatenated streams or trailing data are unsupported",
                    )
                chunk = decoder.unconsumed_tail
        if not decoder.eof:
            raise _decode_types.ResourceDecodeError(
                "invalid_container", "truncated compressed stream"
            )
        return bytes(output)
    except zlib.error as exc:
        raise _decode_types.ResourceDecodeError(
            "invalid_container", "compressed stream integrity check failed"
        ) from exc


def inflate_gzip(data, limit):
    """Read one bounded gzip stream, including its CRC/trailer validation."""
    return _inflate(data, limit, 16 + zlib.MAX_WBITS)


def _member_bytes(data, archive, selected, limit):
    """Validate local header, then inflate without trusting declared output size.

    ZipExtFile truncates output to the central directory's file_size. Use its
    header/overlap checks, but independently decode the entire compressed extent
    so a forged small size and matching prefix CRC cannot conceal extra output.
    """
    with archive.open(selected):
        pass
    offset = selected.header_offset
    if offset < 0 or offset + 30 > len(data):
        raise _decode_types.ResourceDecodeError(
            "invalid_container", "invalid ZIP local header"
        )
    namesize, extrasize = struct.unpack_from("<HH", data, offset + 26)
    start = offset + 30 + namesize + extrasize
    stop = start + selected.compress_size
    if stop > archive.start_dir:
        raise _decode_types.ResourceDecodeError(
            "invalid_container", "ZIP member overlaps directory"
        )
    local_extra = data[offset + 30 + namesize : start]
    position = 0
    while position < len(local_extra):
        if position + 4 > len(local_extra):
            raise _decode_types.ResourceDecodeError(
                "invalid_container", "truncated local extra field"
            )
        kind, size = struct.unpack_from("<HH", local_extra, position)
        position += 4 + size
        if kind == 1:
            raise _decode_types.ResourceDecodeError(
                "unsupported_container", "ZIP64 local member unsupported"
            )
    if position != len(local_extra):
        raise _decode_types.ResourceDecodeError(
            "invalid_container", "invalid local extra field"
        )
    packed = data[start:stop]
    if selected.compress_type == zipfile.ZIP_DEFLATED:
        output = _inflate(packed, limit, -zlib.MAX_WBITS)
    else:
        if len(packed) > limit:
            raise _decode_types.ResourceDecodeError(
                "decoded_limit", "stored ZIP member exceeds byte limit"
            )
        output = packed
    if len(output) != selected.file_size or zlib.crc32(output) != selected.CRC:
        raise _decode_types.ResourceDecodeError(
            "invalid_container", "ZIP length/CRC mismatch"
        )
    return output


def _zip_directory(data, limit):
    """Choose the outer valid directory before any EOCD-shaped archive comment.

    ZIP64/multidisk and prepended/appended data are deliberately unsupported.
    Search only the maximum comment window. Candidate arithmetic alone is not
    evidence of a directory: verify its records before accepting it.
    """
    start = max(0, len(data) - 65557)
    failure = None
    while start < len(data):
        end = data.find(b"PK\x05\x06", start)
        if end < 0:
            break
        start = end + 4
        if end + 22 > len(data):
            continue
        size, offset, comment = struct.unpack_from("<2LH", data, end + 12)
        if end + 22 + comment != len(data) or offset + size != end:
            continue
        try:
            _validate_zip_directory(data, end, limit)
        except _decode_types.ResourceDecodeError as exc:
            if exc.code != "invalid_container":
                raise
            failure = exc
            continue
        # The earliest valid record owns all later bytes as its comment. This
        # prevents a fully plausible fake record inside that comment winning.
        return end
    if failure is not None:
        raise failure
    raise _decode_types.ResourceDecodeError(
        "invalid_container", "missing valid ZIP directory"
    )


def _validate_zip_directory(data, end, limit):
    """Count actual central records before ZipFile allocates its member index."""
    disk, cd_disk, disk_count, count, size, offset, comment = struct.unpack_from(
        "<4H2LH", data, end + 4
    )
    if end + 22 + comment != len(data) or offset + size != end:
        raise _decode_types.ResourceDecodeError(
            "invalid_container", "unsupported ZIP layout or trailing data"
        )
    position, actual = offset, 0
    first_local = None
    while position < end:
        if position + 46 > end or data[position : position + 4] != b"PK\x01\x02":
            raise _decode_types.ResourceDecodeError(
                "invalid_container", "invalid ZIP central record"
            )
        local_offset = struct.unpack_from("<L", data, position + 42)[0]
        first_local = (
            local_offset if first_local is None else min(first_local, local_offset)
        )
        name_size, extra_size, comment_size = struct.unpack_from(
            "<3H", data, position + 28
        )
        position += 46 + name_size + extra_size + comment_size
        actual += 1
    if actual == 0 and offset != 0:
        raise _decode_types.ResourceDecodeError(
            "invalid_container", "empty ZIP has prepended data"
        )
    if position != end:
        raise _decode_types.ResourceDecodeError(
            "invalid_container", "ZIP directory count/size mismatch"
        )
    if actual and (first_local != 0 or data[:4] != b"PK\x03\x04"):
        raise _decode_types.ResourceDecodeError(
            "invalid_container", "ZIP has prepended data or no first local header"
        )
    # Establish the complete candidate's structure before applying format or
    # count policy. Otherwise unsupported-looking bytes inside a member could
    # stop the search before the real directory is reached. Walk twice without
    # allocating an unbounded list of index records.
    position, local_zip64 = offset, False
    while position < end:
        local_zip64 |= _validate_local_layout(data, position, offset)
        lengths = struct.unpack_from("<3H", data, position + 28)
        position += 46 + sum(lengths)
    if local_zip64:
        raise _decode_types.ResourceDecodeError(
            "unsupported_container", "ZIP64 local member unsupported"
        )
    if actual > limit:
        raise _decode_types.ResourceDecodeError(
            "zip_entries_limit", "too many ZIP entries"
        )
    if (
        disk
        or cd_disk
        or disk_count != count
        or count == 65535
        or size == 0xFFFFFFFF
        or offset == 0xFFFFFFFF
    ):
        raise _decode_types.ResourceDecodeError(
            "unsupported_container", "ZIP64/multidisk ZIP unsupported"
        )
    if actual != count:
        raise _decode_types.ResourceDecodeError(
            "invalid_container", "ZIP directory count mismatch"
        )


def _validate_local_layout(data, central, directory):
    """Reject candidate indexes embedded inside the member data they describe.

    Check fixed local metadata and optional data descriptors without inflating.
    Central lengths alone are insufficient: an embedded fake index can claim a
    zero-length member even though the real local header describes more data.
    """
    local = struct.unpack_from("<L", data, central + 42)[0]
    if local + 30 > directory or data[local : local + 4] != b"PK\x03\x04":
        raise _decode_types.ResourceDecodeError(
            "invalid_container", "invalid local header"
        )
    flags, method = struct.unpack_from("<HH", data, central + 8)
    local_flags, local_method = struct.unpack_from("<HH", data, local + 6)
    values = struct.unpack_from("<3L", data, central + 16)
    local_values = struct.unpack_from("<3L", data, local + 14)
    local_zip64 = 0xFFFFFFFF in local_values[1:]
    name_size, extra_size = struct.unpack_from("<HH", data, local + 26)
    central_name_size = struct.unpack_from("<H", data, central + 28)[0]
    stop = local + 30 + name_size + extra_size + values[1]
    if (
        (flags, method) != (local_flags, local_method)
        or stop > directory
        or data[local + 30 : local + 30 + name_size]
        != data[central + 46 : central + 46 + central_name_size]
    ):
        raise _decode_types.ResourceDecodeError(
            "invalid_container", "local/index layout mismatch"
        )
    if local_zip64:
        # Central 32-bit extents can establish layout for this candidate, but
        # ZIP64 remains unsupported. Defer that policy until all entries pass.
        return True
    if not flags & 8:
        if local_values != values:
            raise _decode_types.ResourceDecodeError(
                "invalid_container", "local/index sizes or CRC disagree"
            )
        return False
    # A streaming writer may put zeroes in its local header. Its descriptor
    # must still agree with the candidate index, with or without the signature.
    if any(value not in (0, expected) for value, expected in zip(local_values, values)):
        raise _decode_types.ResourceDecodeError(
            "invalid_container", "invalid streaming local metadata"
        )
    expected = struct.pack("<3L", *values)
    if not (
        stop + 12 <= directory
        and data[stop : stop + 12] == expected
        or stop + 16 <= directory
        and data[stop : stop + 16] == b"PK\x07\x08" + expected
    ):
        raise _decode_types.ResourceDecodeError(
            "invalid_container", "invalid ZIP data descriptor"
        )
    return False


def _safe_member(info):
    name = info.orig_filename
    parts = name.rstrip("/").split("/")
    if (
        not name
        or name.startswith("/")
        or "\\" in name
        or ":" in name
        or any(part in ("", ".", "..") for part in parts)
        or any(ord(char) < 32 or ord(char) == 127 for char in name)
        or name != info.filename
    ):
        raise _decode_types.ResourceDecodeError(
            "unsafe_member", "unsafe ZIP member name"
        )
    if info.volume:
        raise _decode_types.ResourceDecodeError(
            "unsupported_container", "multidisk ZIP member unsupported"
        )
    mode = info.external_attr >> 16
    if stat.S_ISDIR(mode) and not info.is_dir():
        raise _decode_types.ResourceDecodeError(
            "unsafe_member", "directory mode disagrees with member name"
        )
    if stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
        raise _decode_types.ResourceDecodeError(
            "unsafe_member", "ZIP special files are unsupported"
        )
    if info.flag_bits & (1 | 64):
        raise _decode_types.ResourceDecodeError(
            "encrypted_member", "encrypted ZIP members are unsupported"
        )
    if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
        raise _decode_types.ResourceDecodeError(
            "unsupported_container", "only stored/deflated ZIP members are supported"
        )
    # ZIP64 can also be represented in individual extra fields, not only EOCD.
    position = 0
    while position < len(info.extra):
        if position + 4 > len(info.extra):
            raise _decode_types.ResourceDecodeError(
                "invalid_container", "truncated ZIP extra field"
            )
        kind, size = struct.unpack_from("<HH", info.extra, position)
        position += 4 + size
        if kind == 1:
            raise _decode_types.ResourceDecodeError(
                "unsupported_container", "ZIP64 member unsupported"
            )
    if position != len(info.extra):
        raise _decode_types.ResourceDecodeError(
            "invalid_container", "invalid ZIP extra length"
        )


def read_zip(data, options):
    """Read one safe text member; validate the entire bounded member index first."""
    end = _zip_directory(data, options.max_zip_entries)
    # ZipFile also searches for the last signature without validating comments.
    # Give its index reader a comment-free view after our directory validation;
    # member offsets/bytes stay identical and original provenance uses data.
    index_data = data[: end + 20] + b"\x00\x00"
    try:
        with zipfile.ZipFile(io.BytesIO(index_data)) as archive:
            entries = archive.infolist()
            seen, candidates = set(), []
            for info in entries:
                _safe_member(info)
                if info.filename in seen:
                    raise _decode_types.ResourceDecodeError(
                        "ambiguous_member", "duplicate ZIP member names"
                    )
                seen.add(info.filename)
                if info.filename == "META-INF/container.xml":
                    raise _decode_types.ResourceDecodeError(
                        "unsupported_media", "EPUB is byte-retrieval only"
                    )
                if (
                    not info.is_dir()
                    and pathlib.PurePosixPath(info.filename).suffix.lower()
                    in _TEXT_SUFFIXES
                ):
                    candidates.append(info)
            if options.zip_member is not None:
                candidates = [
                    entry
                    for entry in candidates
                    if entry.filename == options.zip_member
                ]
            if len(candidates) != 1:
                raise _decode_types.ResourceDecodeError(
                    "ambiguous_member",
                    "choose one existing safe text ZIP member explicitly",
                )
            selected = candidates[0]
            if selected.file_size > options.max_decoded_bytes:
                raise _decode_types.ResourceDecodeError(
                    "decoded_limit", "ZIP member exceeds byte limit"
                )
            output = _member_bytes(data, archive, selected, options.max_decoded_bytes)
            return (
                bytes(output),
                selected.filename,
                _TEXT_SUFFIXES[pathlib.PurePosixPath(selected.filename).suffix.lower()],
            )
    except (
        zipfile.BadZipFile,
        NotImplementedError,
        RuntimeError,
        UnicodeError,
        ValueError,
        EOFError,
        zlib.error,
    ) as exc:
        raise _decode_types.ResourceDecodeError(
            "invalid_container", "ZIP structure or integrity check failed"
        ) from exc


def unwrap(data, content_encoding, media_types, options):
    """Apply one HTTP coding and at most one container; reject remaining chains."""
    transforms = []
    if content_encoding not in ("", "identity", "gzip"):
        raise _decode_types.ResourceDecodeError(
            "unsupported_content_encoding",
            "only identity or one gzip Content-Encoding is supported",
        )
    if content_encoding == "gzip":
        data = inflate_gzip(data, options.max_decoded_bytes)
        transforms.append("http:gzip")
    detected = (
        "gzip"
        if data.startswith(b"\x1f\x8b")
        else "zip" if data.startswith((b"PK\x03\x04", b"PK\x05\x06")) else "none"
    )
    container = detected if options.container == "auto" else options.container
    if container != detected:
        raise _decode_types.ResourceDecodeError(
            "container_mismatch",
            "container policy disagrees with original-byte signature",
        )
    declared_containers = {
        "application/gzip": "gzip",
        "application/x-gzip": "gzip",
        "application/zip": "zip",
        "application/x-zip-compressed": "zip",
    }
    if any(
        declared_containers[media] != detected
        for media in media_types
        if media in declared_containers
    ):
        raise _decode_types.ResourceDecodeError(
            "container_mismatch", "declared container disagrees with payload signature"
        )
    member, member_media = None, None
    if container == "gzip":
        data = inflate_gzip(data, options.max_decoded_bytes)
        transforms.append("container:gzip")
    elif container == "zip":
        data, member, member_media = read_zip(data, options)
        transforms.append("container:zip")
    if options.zip_member is not None and container != "zip":
        raise _decode_types.ResourceDecodeError(
            "invalid_member", "zip_member requires a ZIP container"
        )
    if len(data) > options.max_decoded_bytes:
        raise _decode_types.ResourceDecodeError(
            "decoded_limit", "payload exceeds decoded byte limit"
        )
    if data.startswith((b"\x1f\x8b", b"PK\x03\x04", b"PK\x05\x06")):
        raise _decode_types.ResourceDecodeError(
            "container_chain", "nested containers are unsupported"
        )
    if data.startswith(
        (b"BZh", b"\xfd7zXZ\x00", b"7z\xbc\xaf\x27\x1c", b"Rar!")
    ) or data[257:263] in (b"ustar\x00", b"ustar "):
        raise _decode_types.ResourceDecodeError(
            "unsupported_container", "container has no supported decoder"
        )
    if data.startswith(b"%PDF-"):
        raise _decode_types.ResourceDecodeError(
            "unsupported_media", "PDF is byte-retrieval only"
        )
    return data, tuple(transforms), member, member_media
