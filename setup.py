import re
from setuptools import setup, find_packages

# Get version from package __init__.py
with open('crossify/__init__.py', 'r') as f:
    __version__ = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                            f.read(), re.MULTILINE).group(1)
if not __version__:
    raise RuntimeError('Cannot find version information')


config = {
    'name': 'crossify',
    'version': __version__,
    'description': ' ',
    'long_description': '\n',
    'author': '',
    'author_email': '',
    'maintainer': '',
    'maintainer_email': '',
    'url': '',
    'license': 'MIT / Apache 2.0',
    'download_url': '',
    'install_requires': ['pandas',
                         'geopandas',
                         'numpy',
                         'rtree',
                         'Shapely'],
    'packages': find_packages(),
    'include_package_data': True,
    'classifiers': ['Programming Language :: Python',
                    'Programming Language :: Python :: 3.5',
                    'Programming Language :: Python :: 3 :: Only'],
    'zip_safe': False
}

setup(test_suite='nose.collector',
      **config)

# ,
#     'entry_points': '''
#         [console_scripts]
#         sidewalkify=sidewalkify.__main__:sidewalkify
# '''
