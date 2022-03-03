#!/usr/bin/env python

from setuptools import setup

setup(
    name='thin-edge-file-management',
    version='1.0',
    description='A thin-edge.io plugin to manage configuration and log files',
    author='Tobias Sommer',
    author_email='',
    url='',
    packages=[
        'thin_edge_file_management'
    ],
    install_requires=[
        'paho-mqtt',
        'pyjwt',
        'pyyaml',
        'requests',
        'toml'
    ],
    entry_points = {
        'console_scripts': [
            'thin-edge-file-management = thin_edge_file_management.runner:start'
        ],
    },

    

)