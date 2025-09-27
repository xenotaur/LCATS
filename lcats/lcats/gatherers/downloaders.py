"""Data gathering utility functions."""
import abc
import codecs
import json
import os
import hashlib
import shutil
from urllib.parse import urlparse, unquote

import chardet
import requests

import lcats.constants as constants


def detect_url_encoding(url, timeout=10):
    """Get the encoding of a page from a URL.

    Args:
        url (str): The URL to check.
        timeout (int): The number of seconds to wait for a response.

    Returns:
        str: The encoding of the page, or None if it couldn't be determined.
    """
    response = requests.head(url, timeout=timeout)
    if response.status_code == 200:
        return response.encoding
    else:
        print(
            f"Failed to get the encoding. Status code: {response.status_code}")
        return None


def detect_encoding(text):
    """Detect the encoding of a text string."""
    # If text is a string, encode it to bytes for detection
    if isinstance(text, str):
        text = text.encode('utf-8', errors='ignore')

    # Use chardet to detect encoding
    detected = chardet.detect(text)
    return detected['encoding']


def convert_encoding(text, source_encoding='utf-8', target_encoding='ISO-8859-1'):
    """Convert the encoding of a text string from source to target encoding."""
    # Decode the text from source encoding, then re-encode in target encoding
    try:
        # Confirm we have valid input and output codecs
        codecs.lookup(source_encoding)
        codecs.lookup(target_encoding)

        # If text is bytes, decode it first; otherwise, assume it's already decoded
        if isinstance(text, bytes):
            text = text.decode(source_encoding, errors='strict')
        # Encode in the target encoding
        converted_text = text.encode(target_encoding, errors='strict')
        return converted_text
    except (UnicodeEncodeError, UnicodeDecodeError, LookupError) as e:
        print(f"Error converting text encoding: {e}")
        return None


def load_page(url, timeout=10, force_encoding=None):
    """Load a page from a URL and return the text content.

    Args:
        url (str): The URL to load.
        timeout (int): The number of seconds to wait for a response.
        force_encoding (str): The encoding to use for the response.

    Returns:
        str: The text content of the page.
    """
    response = requests.get(url, timeout=timeout)
    if force_encoding:
        response.encoding = force_encoding
    if response.status_code == 200:
        print("File successfully downloaded.")
        return response.text
    else:
        print(
            f"Failed to download the file. Status code: {response.status_code}")
        return None


def filename_from_url(url):
    """Generate a unique filename from a URL."""
    # Parse the URL
    parsed_url = urlparse(url)

    # Extract the path and query to form the base of the filename
    url_path = unquote(parsed_url.path)
    url_query = unquote(parsed_url.query)

    # Combine path and query to form a unique identifier
    unique_string = url_path + '?' + url_query if url_query else url_path

    # Create a hash of the unique string
    url_hash = hashlib.sha256(unique_string.encode('utf-8')).hexdigest()

    # Get the file extension (if any) from the URL path
    file_extension = os.path.splitext(parsed_url.path)[1]

    # Combine the hash with the file extension to form the filename
    filename = f"{url_hash}{file_extension}"

    return filename


class ResourceCache(abc.ABC):
    """Utility class to cache resources in a directory."""

    def __init__(self,
                 root=constants.CACHE_ROOT,
                 encoding=constants.TEXT_ENCODING):
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
        with open(full_path, 'w', encoding=self.encoding) as file:
            file.write(acquired)

    def cache(self, resource, force=False):
        """If a file doesn't already exist, get it from the resource."""
        file_name = self.canonicalize(resource)
        file_exists, full_path = self.ensure(file_name)

        if not file_exists or force:
            self.store(resource, full_path)
            print(f"Resource {resource} saved to {file_name} .")
        else:
            print(
                f"Resource {resource} exists at {file_name} , skipping download.")
        return full_path

    def get(self, resource, force=False):
        """Get the contents of a file if it exists, otherwise acquire it."""
        full_path = self.cache(resource, force=force)
        with open(full_path, 'r', encoding=self.encoding) as file:
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
                    print(f'Failed to delete {file_path}. Reason: {e}')
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
            canonicalizer=filename_from_url,
            acquirer=lambda url: load_page(url, force_encoding=self.encoding),
            **kwargs)


class DataGatherer:
    """Utility class to download data files if needed to a given directory."""

    def __init__(self,
                 name,
                 description=None,
                 root=constants.DATA_ROOT,
                 cache=constants.CACHE_ROOT,
                 suffix=".json",
                 license=None):
        """Initialize the gatherer with a name, description, and root directory.

        Args:
            name: The name of the gatherer.
            description: A description of the gatherer.
            root: The root directory where the data will be stored.
            suffix: The file extension to use for the data files.
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
            with open(license_path, 'w', encoding='utf-8') as license_file:
                license_file.write(
                    self.license if self.license else "No license provided.")

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
                "metadata": additional_data
            }

            # Write data to JSON file
            with open(file_path, 'w', encoding='utf-8') as json_file:
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
            with open(file_path, 'r', encoding='utf-8') as json_file:
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
                    print(f'Failed to delete {self.path}. Reason: {e}')
            print(f"Cleared all contents in {self.path}")
        else:
            print(f"Directory {self.path} does not exist, nothing to clear.")

    def gather(self, extractors):
        """Gather a set of resources from a list of extractor objects."""
        # Lovecraft is []
