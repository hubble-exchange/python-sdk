import pathlib
from setuptools import setup

HERE = pathlib.Path(__file__).parent
README = (HERE / "README.md").read_text()


setup(
    name='hubble_exchange',
    version='0.1dev',
    author='lumos',
    author_email='lumos@hubble.exchange',
    packages=['hubble_exchange'],
    # scripts=['first.py'],
    license='LICENSE',
    description='Official python SDK for Hubble Exchange',
    long_description=README,
    url='https://hubble.exchange',
    include_package_data=True,
    install_requires=[
        "web3 >= 6.5.0",
        "eth_typing >= 3.4.0",
        "eth_account >= 0.8.0",
        "requests >= 2.31.0",
        "websocket-client >= 1.6.0",
    ],
)
