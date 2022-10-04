import inspect
import os

from setuptools import setup

__location__ = os.path.join(os.getcwd(), os.path.dirname(inspect.getfile(inspect.currentframe())))

VERSION = "0.0.1"


def read_requirements():
    with open("requirements.txt", "r") as fh:
        requirements = fh.readlines()
        return [
            req.split("==")[0]
            for req in requirements
            if req.strip() != "" and not req.strip().startswith("#")
        ]


setup(
    description="API and command line tools to interact with the https://n26.com/ API",
    long_description="API and command line tools to interact with the https://n26.com/ API",
    author="Felipe Neut",
    author_email="fneutm@gmail.com",
    version=VERSION,
    install_requires = ["tabulate==0.8.9"], 
    #install_requires=read_requirements(),
    packages=["n26"],
    scripts=[],
    name="n26",
    entry_points={
        "console_scripts": ["n26 = n26.cli:cli"]
    },  # from n26.cli package, the function cli
)
