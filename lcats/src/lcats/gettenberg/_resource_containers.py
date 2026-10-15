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
    """Count actual central records before ZipFile allocates its member index.

    ZIP64/multidisk and prepended/appended data are deliberately unsupported.
    Do not trust the declared entry count: ZipFile itself parses until size_cd.
    """
    end = data.rfind(b"PK\x05\x06", max(0, len(data) - 65557))
    if end < 0 or end + 22 > len(data):
        raise _decode_types.ResourceDecodeError(
            "invalid_container", "missing ZIP directory"
        )
    disk, cd_disk, disk_count, count, size, offset, comment = struct.unpack_from(
        "<4H2LH", data, end + 4
    )
    if end + 22 + comment != len(data) or offset + size != end:
        raise _decode_types.ResourceDecodeError(
            "invalid_container", "unsupported ZIP layout or trailing data"
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
    position, actual = offset, 0
    while position < end:
        if position + 46 > end or data[position : position + 4] != b"PK\x01\x02":
            raise _decode_types.ResourceDecodeError(
                "invalid_container", "invalid ZIP central record"
            )
        name_size, extra_size, comment_size = struct.unpack_from(
            "<3H", data, position + 28
        )
        position += 46 + name_size + extra_size + comment_size
        actual += 1
        if actual > limit:
            raise _decode_types.ResourceDecodeError(
                "zip_entries_limit", "too many ZIP entries"
            )
    if position != end or actual != count:
        raise _decode_types.ResourceDecodeError(
            "invalid_container", "ZIP directory count/size mismatch"
        )


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
    _zip_directory(data, options.max_zip_entries)
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
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
    if container == "none" and any(
        media
        in (
            "application/gzip",
            "application/x-gzip",
            "application/zip",
            "application/x-zip-compressed",
        )
        for media in media_types
    ):
        raise _decode_types.ResourceDecodeError(
            "container_mismatch", "declared container has no matching signature"
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
