# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open("README.md", "r",encoding='utf-8') as fh:
    long_description = fh.read()


setup(
    name="asyncpy",
    url="https://github.com/lixi5338619/asyncpy.git",
    version= '1.1.7',
    description="Use asyncio and aiohttp's concatenated web crawler framework",
    long_description=long_description,
    author="lx",
    author_email="125066648@qq.com",
    keywords="python web crawl asyncio",
    maintainer='lx',
    packages = find_packages(),
    platforms=["all"],

    install_requires=[
        'lxml',
        'parsel',
        'docopt',
        'aiohttp',
        ],
    python_requires='>=3.6',
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    entry_points={'console_scripts': [
        'asyncpy = asyncpy.__init__:cli',
    ]},
)


## python setup.py sdist bdist_wheel
## twine upload dist/*
