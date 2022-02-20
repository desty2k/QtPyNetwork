from setuptools import find_packages, setup

from QtPyNetwork import __version__

with open("README.rst", "r", encoding="utf-8") as f:
    doc = f.read()

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
    long_description_content_type='text/x-rst',
    python_requires='>=3.6',
    zip_safe=False,
    classifiers=[
        'Development Status :: 5 - Production/Stable',

        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',

        'Programming Language :: Python :: Implementation :: CPython',

        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',

        'Topic :: Software Development :: Libraries :: Python Modules',

    ],
    keywords=['server',
              'client',
              'pyqt5',
              'pyside2',
              'qtpy',
              'tcp'],
    project_urls={
        "Issues": "https://github.com/desty2k/QtPyNetwork/issues",
        "Docs": "https://desty2k.github.io/QtPyNetwork/",
    }
)
