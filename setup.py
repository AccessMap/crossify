# -*- coding: utf-8 -*-
from setuptools import setup

packages = \
['crossify']

package_data = \
{'': ['*']}

install_requires = \
['click>=7.0.0,<8.0.0',
 'geopandas>=0.8,<0.9',
 'numpy>=1.12.1,<2.0.0',
 'osmnx>=0.14,<0.15',
 'overpass>=0.5.6,<0.6.0',
 'shapely>=1.6,<2.0']

entry_points = \
{'console_scripts': ['crossify = crossify.cli:crossify']}

setup_kwargs = {
    'name': 'crossify',
    'version': '0.1.4',
    'description': 'Generate street crossing lines, either from OpenStreetMap or using a file of sidewalk lines',
    'long_description': None,
    'author': 'Nick Bolten',
    'author_email': 'nbolten@gmail.com',
    'maintainer': None,
    'maintainer_email': None,
    'url': None,
    'packages': packages,
    'package_data': package_data,
    'install_requires': install_requires,
    'entry_points': entry_points,
    'python_requires': '>=3.6.1,<4.0.0',
}


setup(**setup_kwargs)

# This setup.py was autogenerated using poetry.
