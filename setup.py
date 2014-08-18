from distutils.core import setup
from setuptools import find_packages

setup(
    name='django-socolissimo',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    url='https://github.com/oracom/django-socolissimo',
    description='Client for the labeling webservice from SoColissimo',
    long_description=open('README.md').read(),
    install_requires=[
        "Django",
        "suds-jurko >= 0.6",
        "requests",
    ]
)
