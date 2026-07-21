"""Setuptools setup.py is an older variant of pyproject.toml."""

from setuptools import setup, find_packages

setup(
    name="lcats",
    version="0.1",
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'lcats=lcats.cli:main',
        ],
    },
    install_requires=[
        # List your dependencies here
    ],
    author="Anthony Francis",
    author_email="centaur@logicalrobotics.com",
    description="Literary Captain's Advisory Tool System.",
    long_description=open('README.md', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    url="https://github.com/xenotaur/LCATS",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.10',
)
