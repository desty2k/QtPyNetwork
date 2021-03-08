from setuptools import find_packages, setup

from QtPyNetwork import __version__
from QtPyNetwork import __doc__ as doc

setup(
    name='QtPyNetwork',
    version=__version__,
    packages=find_packages(),
    url='',
    license='MIT',
    author='Wojciech Wentland',
    author_email='wojciech.wentland@int.pl',
    description='Abstraction layer for Python Qt networks.',
    long_description=doc,
    python_requires='>=3.5',
    zip_safe=False
)
