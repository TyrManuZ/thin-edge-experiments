#!/usr/bin/env python

from setuptools import setup

setup(
    name='thin_edge_example_python_module',
    version='1.0',
    description='A simple example to create a thin-edge module written in python',
    author='Tobias Sommer',
    author_email='',
    url='',
    packages=[
        'example'
    ],
    install_requires=[
        'paho-mqtt',
    ],
    entry_points = {
        'console_scripts': [
            'thin-edge-module-example = example.example:send_message'
        ],
    },

    

)