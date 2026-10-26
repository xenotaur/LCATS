"""Publish a new story without truncating or replacing an existing output."""

import json
import os
import pathlib
import tempfile


def existing(path):
    """Reuse only an existing regular non-symlink file; do not validate its content."""
    path = pathlib.Path(path)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise OSError(f"story output is not a regular file: {path}")
    return path.is_file()


def publish(path, data):
    """Atomically publish complete JSON if absent, preserving concurrent outputs.

    Uses a same-directory temporary file and atomic hard-link creation, matching
    the original-byte store's filesystem requirement. File contents are fsynced;
    this does not promise power-loss durability of directory entries. Temporary
    files are removed on serialization/publication failure. Existing files are
    intentionally preserved without claiming their JSON is valid.

    Returns:
        True when this call publishes; False when an existing or concurrently
        published file is preserved. Errors still propagate.
    """
    path = pathlib.Path(path)
    if existing(path):
        return False
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=".story-",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = pathlib.Path(stream.name)
            json.dump(data, stream, indent=4)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if not existing(path):
                raise
            return False
        return True
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
