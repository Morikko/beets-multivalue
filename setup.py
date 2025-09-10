from setuptools import find_packages, setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="beets-multivalue",
    version="0.2.0",
    author="Eric Masseran",
    description="A beet plugin to manage multi-value fields",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Morikko/beets-multivalue",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    install_requires=["beets>2"],
    license="MIT",
)
