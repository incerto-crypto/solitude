import setuptools

# DO NOT remove or rename this variable
VERSION = "0.0.1"


SETUP = lambda: dict(
    name="solitude",
    version=VERSION,
    author="Solitude Developers",
    author_email="alpacaplumber@gmail.com",
    description="""Solidity contract test framework""",
    long_description_markdown_filename='README.md',
    url="https://github.com/incerto-crypto/solitude",
    packages=setuptools.find_packages(exclude=["tests"]),
    zip_safe=False,
    license="BSD-3-Clause",
    license_file="COPYING",
    package_data={
        "solitude": ["_internal/resources/*"]
    },
    setup_requires=[
        'setuptools-markdown'],
    python_requires='>=3.5, <4',
    install_requires=[
        "web3==4.8.3",
        "requests",
        "pyyaml",
        "pytest",
        "pystache",
        "colorama",
        "jsonschema"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: BSD License"
    ],
    entry_points={
        "console_scripts": [
            "solitude=solitude.cli.main:main"]
    }
)


if __name__ == "__main__":
    setuptools.setup(**SETUP())
