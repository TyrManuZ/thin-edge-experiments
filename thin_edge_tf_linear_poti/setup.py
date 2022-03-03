#!/usr/bin/env python

from setuptools import setup

setup(
    name='thin-edge-tf-linear-poti',
    version='1.0',
    description='A thin-edge.io plugin to integrate TinkerForge Linear Poti',
    author='Tobias Sommer',
    author_email='',
    url='',
    packages=[
        'thin_edge_tf_linear_poti'
    ],
    install_requires=[
        'paho-mqtt',
        'tinkerforge'
    ],
    entry_points = {
        'console_scripts': [
            'thin-edge-tf-linear-poti = thin_edge_tf_linear_poti.runner:read_linear_poti'
        ],
    },

    

)