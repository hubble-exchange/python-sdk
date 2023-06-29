## Setup pypirc

Go to pypi.org and login to create API keys and then create a file called `.pypirc` in your home directory and add the following content to it:


## Steps to build and publish

```shell
# create a new package
python3 -m build

# test the release
# make sure dist dir doesn't have any previous packages cuz only one package can be uploaded at a time
python3 -m twine upload --repository testpypi dist/*

# test this package by installing it from testpypi like this:
pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple hubble-exchange==0.1.0.dev0

# release on pypi - this is like production release
python3 -m twine upload --repository pypi dist/*
```
