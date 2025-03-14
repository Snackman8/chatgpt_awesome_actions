#!/usr/bin/env python

from setuptools import setup

def read_requirements():
    with open("requirements.txt") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(name='chatgpt_awesome_actions',
      version='1.0.0',
      description='ChatGPT Awesome Actions',
      packages=['chatgpt_awesome_actions_datamodules', 'chatgpt_awesome_actions_monitoring_webapp'],
      install_requires=read_requirements(),
      package_data={
        "chatgpt_awesome_actions_datamodules": ["_static/**/*"],  # Include all files inside _static
        "chatgpt_awesome_actions_monitoring_webapp": ["*.html"],  # Includes all .html files in this package
      },
      entry_points={
        'console_scripts': ['chatgpt_awesome_actions_monitor=chatgpt_awesome_actions_monitoring_webapp.webapp_chatgpt_awesome_actions_monitoring:console_entry'],
        }      
)
