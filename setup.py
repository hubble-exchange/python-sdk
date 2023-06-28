import pathlib
from setuptools import setup
HERE = pathlib.Path(__file__).parent
README = (HERE / "README.md").read_text()


setup(
    name='hubble-exchange',
    version='0.1dev',
    author='lumos',
    author_email='lumos@hubble.exchange',
    packages=['hubble'],
    # scripts=['first.py'],
    license='LICENSE',
    description='Official python SDK for Hubble Exchange',
    long_description=README,
    url='https://hubble.exchange'
    # install_requires=[
    #     "web3 == 6.5.0",
    #     "caldav == 0.1.4",
    # ],
)
