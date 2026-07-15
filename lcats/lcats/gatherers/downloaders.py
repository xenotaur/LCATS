"""Data gathering utility functions."""

import abc
import json
import os
import shutil

import requests

from lcats import constants
from lcats.gatherers import normalization
from lcats.utils import env
from lcats.utils import names


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

    def __init__(
        self, root=env.cache_resources_dir(), encoding=constants.TEXT_ENCODING
    ):
        """Initialize the downloader with a root directory.

        Args:
            root: The root directory where the data will be stored.
            encoding: The encoding to use for the files.
        """
        self.root = root
        self.encoding = encoding

    def full_path(self, filename):
        """Return the full path to the file in the cache."""
        return os.path.join(self.root, filename)

    def ensure(self, filename):
        """Ensure the directory tree exists and whether the file is there."""
        # Create the root directory if it doesn't exist

        if not os.path.exists(self.root):
            os.makedirs(self.root)

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

    def __init__(self, **kwargs):
        """Initialize the downloader with a root directory."""
        super().__init__(
            canonicalizer=names.url_to_filename,
            acquirer=load_page,
            **kwargs,
        )


class DataGatherer:
    """Utility class to download data files if needed to a given directory."""

    def __init__(
        self,
        name,
        description=None,
        root=env.data_root(),
        cache=env.cache_resources_dir(),
        suffix=".json",
        license=None,
    ):
        """Initialize the gatherer with a name, description, and root directory.

        Args:
            name: The name of the gatherer.
            description: A description of the gatherer.
            root: The root directory where the data will be stored.
            suffix: The file extension to use for the data files.
            license: The license to include in the gatherer's directory.
        """
        self.name = name
        self.description = description
        self.root = root
        self.cache = cache
        self.suffix = suffix
        self.license = license
        self.resources = {}
        self.downloads = {}
        self.resource_cache = UrlResourceCache(root=self.cache)

    @property
    def path(self):
        """Return the full path to the gatherer's directory."""
        return os.path.join(self.root, self.name)

    def ensure(self, filename):
        """Ensure the directory tree exists and whether the file is there."""
        # Create the root directory if it doesn't exist
        if not os.path.exists(self.root):
            os.makedirs(self.root)

        # Create the subdirectory if provided and doesn't exist
        if not os.path.exists(self.path):
            os.makedirs(self.path)

        # Create the license file if it doesn't exist
        license_path = os.path.join(self.path, constants.LICENSE_FILE)
        if not os.path.exists(license_path):
            with open(license_path, "w", encoding="utf-8") as license_file:
                license_file.write(
                    self.license if self.license else "No license provided."
                )

        # Check if the file exists
        file_path = os.path.join(self.path, filename + self.suffix)
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
            # regeneration, not stored as a one-off.
            normalization.normalize_story_dict(
                data_to_save,
                collection=self.name,
                story_id=os.path.splitext(filename)[0],
            )

            # Write data to JSON file
            with open(file_path, "w", encoding="utf-8") as json_file:
                json.dump(data_to_save, json_file, indent=4)
            print(f"File {file_path} saved")
            self.downloads[filename] = file_path
        else:
            print(f"File {file_path} exists, skipping download.")

    def get(self, filename, callback, force=False):
        """Get the contents of a file if it exists, otherwise download it."""
        file_exists, file_path = self.ensure(filename)
        if not file_exists or force:
            self.download(filename, callback, force)
        else:
            with open(file_path, "r", encoding="utf-8") as json_file:
                return json.load(json_file)

    def clear(self):
        """Clear the contents of the gatherer's directory."""
        if os.path.exists(self.path):
            # Remove all contents of the directory
            for filename in os.listdir(self.path):
                file_path = os.path.join(self.path, filename)
                try:
                    if os.path.isfile(self.path) or os.path.islink(self.path):
                        os.unlink(file_path)  # Remove the file or link
                    elif os.path.isdir(self.path):
                        shutil.rmtree(self.path)  # Remove the directory
                except Exception as e:
                    print(f"Failed to delete {self.path}. Reason: {e}")
            print(f"Cleared all contents in {self.path}")
        else:
            print(f"Directory {self.path} does not exist, nothing to clear.")

    def gather(self, extractor):
        """Gather a resource from an extractor object."""
        # For each extractor, we should do the following:
        #  - Compute a unique name for each object
        #    - This should be a resource, name tuple
        #    - The name must be unique within the gatherer
        raise NotImplementedError("Gather method not implemented yet.")
