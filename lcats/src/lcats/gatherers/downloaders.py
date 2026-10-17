"""Data gathering utility functions."""

import abc
import json
import os
import shutil

import requests

from lcats import constants
from lcats.analysis.corpus import discovery
from lcats.gatherers import normalization
from lcats.gettenberg import resources as source_resources
from lcats.utils import env
from lcats.utils import names
from lcats.utils import paths


def load_page(url, timeout=10, preferred_encoding="utf-8"):
    """Load a page from a URL and return decoded text content.

    Args:
        url (str): The URL to load.
        timeout (int): The number of seconds to wait for a response.
        preferred_encoding (str): The encoding to try first when decoding.

    Returns:
        str: The decoded text content of the page.
    """
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()

    raw = response.content

    try:
        text = raw.decode(preferred_encoding)
        encoding_used = preferred_encoding
    except UnicodeDecodeError as exception:
        encoding_used = response.apparent_encoding or response.encoding
        if not encoding_used:
            raise UnicodeDecodeError(
                "unknown", raw, 0, 1, "Unable to determine response encoding"
            ) from exception
        text = raw.decode(encoding_used, errors="replace")

    print(f"File successfully downloaded using encoding {encoding_used}.")
    return text


class ResourceCache(abc.ABC):
    """Utility class to cache resources in a directory."""

    def __init__(self, root=None, encoding=constants.TEXT_ENCODING):
        """Initialize the downloader with a root directory.

        Args:
            root: Storage directory; None resolves the environment at construction.
            encoding: The encoding to use for the files.
        """
        self.root = env.cache_resources_dir() if root is None else root
        self.encoding = encoding

    def full_path(self, filename):
        """Return the full path to the file in the cache."""
        return os.path.join(self.root, filename)

    def ensure(self, filename):
        """Ensure the directory tree exists and whether the file is there."""
        # Create the root directory if it doesn't exist
        paths.makedirs(self.root)

        # Check if the file exists
        full_path = self.full_path(filename)
        return os.path.exists(full_path), full_path

    @abc.abstractmethod
    def canonicalize(self, resource):
        """Canonicalize the resource name as a file we can save."""

    @abc.abstractmethod
    def acquire(self, resource):
        """Get the contents of the resource."""

    def store(self, contents, full_path):
        """Store the contents of the resource at the full path."""
        acquired = self.acquire(contents)
        print(f"Acquired {len(acquired)} bytes from {contents}")
        print(f"Storing at {full_path} with encoding {self.encoding}")
        with open(full_path, "w", encoding=self.encoding) as file:
            file.write(acquired)

    def cache(self, resource, force=False):
        """If a file doesn't already exist, get it from the resource."""
        file_name = self.canonicalize(resource)
        file_exists, full_path = self.ensure(file_name)

        if not file_exists or force:
            self.store(resource, full_path)
            print(f"Resource {resource} saved to {file_name} .")
        else:
            print(f"Resource {resource} exists at {file_name} , skipping download.")
        return full_path

    def get(self, resource, force=False):
        """Get the contents of a file if it exists, otherwise acquire it."""
        full_path = self.cache(resource, force=force)
        with open(full_path, "r", encoding=self.encoding) as file:
            return file.read()

    def clear(self):
        """Clear the contents of the gatherer's directory."""
        if os.path.exists(self.root):
            # Remove all contents of the directory
            for filename in os.listdir(self.root):
                file_path = os.path.join(self.root, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)  # Remove the file or link
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)  # Remove the directory
                except Exception as e:
                    print(f"Failed to delete {file_path}. Reason: {e}")
            print(f"Cleared all contents in {self.root}")
        else:
            print(f"Directory {self.root} does not exist, nothing to clear.")


class LambdaResourceCache(ResourceCache):
    """Utility class to cache URL-loadable resources in a directory."""

    def __init__(self, canonicalizer, acquirer, **kwargs):
        """Initialize the downloader with a root directory.

        Args:
            canonicalizer: A function to convert a resource to a filename.
            acquirer: A function to get the contents of a resource.
        """
        super().__init__(**kwargs)
        self.canonicalizer = canonicalizer
        self.acquirer = acquirer

    def canonicalize(self, resource):
        """Canonicalize the resource URL as a file we can save."""
        return self.canonicalizer(resource)

    def acquire(self, resource):
        """Acquire the resource from an URL and return the text content."""
        return self.acquirer(resource)


class UrlResourceCache(LambdaResourceCache):
    """Utility class to cache URL-loadable resources in a directory."""

    def __init__(self, *, offline=False, **kwargs):
        """Use cached HTML offline, refusing any acquisition on a cache miss."""
        if type(offline) is not bool:
            raise ValueError("offline must be bool")
        self.offline = offline
        super().__init__(
            canonicalizer=names.url_to_filename, acquirer=load_page, **kwargs
        )

    def acquire(self, resource):
        """Enforce policy at the actual network boundary, including force calls."""
        if self.offline:
            raise source_resources.ResourcePolicyError(
                "offline_cache_miss",
                "HTML source is not cached; offline gathering cannot download it",
            )
        return super().acquire(resource)


class DataGatherer:
    """Utility class to download data files if needed to a given directory."""

    def __init__(
        self,
        name,
        description=None,
        root=None,
        cache=None,
        suffix=".json",
        license=None,
        offline=False,
    ):
        """Initialize the gatherer with a name, description, and root directory.

        Args:
            name: The name of the gatherer.
            description: A description of the gatherer.
            root: Data directory; None resolves LCATS_DATA_DIR at construction.
            cache: HTML cache directory; None resolves the current cache root.
            offline: Refuse HTML acquisition while allowing cached content.
            suffix: The file extension to use for the data files.
            license: The license to include in the gatherer's directory.
        """
        self.name = name
        self.description = description
        self.root = env.data_root() if root is None else root
        self.cache = env.cache_resources_dir() if cache is None else cache
        self.suffix = suffix
        self.license = license
        self.resources = {}
        self.downloads = {}
        self.resource_cache = UrlResourceCache(root=self.cache, offline=offline)

    @property
    def path(self):
        """Return the full path to the gatherer's directory."""
        return os.path.join(self.root, self.name)

    def ensure(self, filename):
        """Ensure the story's bucket directory exists and whether its canonical
        file is there.

        Writes to ``<collection>/<filename>/story.json`` (Decision 8 of
        PROP-LCATS-STORY-BUCKET-LAYOUT) rather than the old flat
        ``<collection>/<filename><suffix>`` path -- ``filename`` names the
        story's own subdirectory now, not a leaf file stem. ``self.suffix``
        no longer affects the write path at all: the leaf filename is
        always the reserved canonical name, never ``filename + self.suffix``
        -- ``suffix`` is retained only as a constructor parameter/attribute
        for backward compatibility, not consulted here.
        """
        # Create the root directory if it doesn't exist
        paths.makedirs(self.root)

        # Create the subdirectory if provided and doesn't exist
        paths.makedirs(self.path)

        # Create the license file if it doesn't exist
        license_path = os.path.join(self.path, constants.LICENSE_FILE)
        if not os.path.exists(license_path):
            with open(license_path, "w", encoding="utf-8") as license_file:
                license_file.write(
                    self.license if self.license else "No license provided."
                )

        # Create the story's own bucket directory and point at its canonical
        # file -- the leaf filename is always the reserved canonical name,
        # not filename + self.suffix.
        story_dir = os.path.join(self.path, filename)
        paths.makedirs(story_dir)
        file_path = os.path.join(story_dir, discovery.CANONICAL_STORY_FILENAME)
        return os.path.exists(file_path), file_path

    def resource(self, resource, force=False):
        """Get the contents of a file if it exists, otherwise acquire it."""
        return self.resource_cache.get(resource, force=force)

    def download(self, filename, resource, handler, force=False):
        """If a file doesn't already exist, get its resource and process it with the handler."""
        file_exists, file_path = self.ensure(filename)

        if not file_exists or force:
            # Get the resource from the URL
            contents = self.resource(resource, force=force)

            # Execute the callback to get the data to save
            descriptive_name, body_text, additional_data = handler(contents)
            if body_text is None:
                raise ValueError(f"Failed to download {descriptive_name}")

            # Structure the data into a dictionary
            data_to_save = {
                "name": descriptive_name,
                "body": body_text,
                "metadata": additional_data,
            }

            # Apply replayable gather-time repairs (rules + per-story overrides)
            # before the first write so the fix is reproduced on every
            # regeneration, not stored as a one-off. story_id is the
            # canonical story name (filename) itself, threaded straight
            # through -- never re-derived from the write path's leaf name,
            # which is always the reserved canonical filename post-migration
            # and would collapse every story onto one overrides key
            # (Decision 7 of PROP-LCATS-STORY-BUCKET-LAYOUT).
            normalization.normalize_story_dict(
                data_to_save,
                collection=self.name,
                story_id=filename,
            )

            # Write data to JSON file
            with open(file_path, "w", encoding="utf-8") as json_file:
                json.dump(data_to_save, json_file, indent=4)
            print(f"File {file_path} saved")
            self.downloads[filename] = file_path
        else:
            print(f"File {file_path} exists, skipping download.")

    def get(self, filename, resource, handler, force=False):
        """Get the contents of a file if it exists, otherwise download it."""
        file_exists, file_path = self.ensure(filename)
        if not file_exists or force:
            self.download(filename, resource, handler, force)
        with open(file_path, "r", encoding="utf-8") as json_file:
            return json.load(json_file)

    def clear(self):
        """Remove the gatherer's directory (and everything in it)."""
        if os.path.exists(self.path):
            try:
                shutil.rmtree(self.path)
                print(f"Removed {self.path}")
            except Exception as e:
                print(f"Failed to delete {self.path}. Reason: {e}")
        else:
            print(f"Directory {self.path} does not exist, nothing to clear.")

    def gather(self, extractor):
        """Gather a resource from an extractor object."""
        # For each extractor, we should do the following:
        #  - Compute a unique name for each object
        #    - This should be a resource, name tuple
        #    - The name must be unique within the gatherer
        raise NotImplementedError("Gather method not implemented yet.")
