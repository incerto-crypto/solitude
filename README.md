# Solitude `preview`

[![Build Status](https://travis-ci.com/incerto-crypto/solitude.svg?branch=master)](https://travis-ci.com/incerto-crypto/solitude)  [![Documentation Status](https://readthedocs.org/projects/solitude/badge/?version=master)](https://solitude.readthedocs.io/en/master/?badge=master)

`[Warning]` This project is currently in alpha stage.

A Python-based development framework to deploy, interact, test and debug your Solidity contracts. 

## Quick start

`[Note]` If you are starting from scratch, see the examples and step-by-step tutorial at `solitude-examples`.

### Install

Install solitude from git into your python3 virtual environment

```bash
pip install git+https://github.com/incerto-crypto/solitude.git
```

This package depends on web3 for python, which in turn depends on packages that need to be compiled from source. You may need to install development tools and python headers first.

On Windows, install "Visual C++ Build Tools 2015". Also install 'pywin32' in your python virtual environment.


### Run Tests

From within a python virtualenv with solitude installed, in the project root directory, run

```bash
pytest -v tests
```

### Build docker

The docker image will be named `solitude-{VERSION}-dev`, according to `VERSION` in `setup.py`.

```bash
make docker-build
```

## Documentation

Coming soon

## Contributing

Coming soon
