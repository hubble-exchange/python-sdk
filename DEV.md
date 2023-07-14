## Setup pypirc

Go to pypi.org(and test.pypi.org) and login to create API keys and then create a file called `.pypirc` in your home directory and add the keys

```
# ~/.pypirc

[testpypi]
  username = __token__
  password = <api_key>

[pypi]
  username = __token__
  password = <api_key>
```

## Steps to build and publish

```shell
# build a new package, version number needs to be updated in pyproject.toml before this
python3 -m build

# test the release
# make sure dist dir doesn't have any previous packages cuz only one package can be uploaded at a time
# check the current version number on https://test.pypi.org/project/hubble-exchange/
python3 -m twine upload --repository testpypi dist/*

# test this package by installing it from testpypi like this:
pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple hubble-exchange==0.1.0.dev0

# release on pypi - this is like production release
# check the current version number on https://pypi.org/project/hubble-exchange/ and update the version number in pyproject.toml accordingly
python3 -m twine upload --repository pypi dist/*

# create a new virtual env and test it by installing like this:
pip install hubble-exchange==0.2.0
```

## Tests

Needs pytest library to be installed in the virtual environment, not globally.
```shell
pip install pytest
```

Run the tests like this:
```shell
python -m pytest tests/orderbook.py
```
