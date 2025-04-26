from setuptools import find_packages, setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="beets-multivalue",
    version="0.1.0-dev0",
    author="Eric MASSERAN",
    description="A beet plugin to manage multi-value fields",
    long_description=long_description,
    long_description_content_type="text/markdown",
    # url="https://github.com/...",
    packages=find_packages(),
    classifiers=[
        # TODO: Python version definition
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    install_requires=["beets>2"],
    # TODO: License file
)
