import os
from setuptools import setup
from os.path import join
import sys


__author__ = "Ralph Schmieder"
__author_email__ = "rschmied@cisco.com"
__copyright__ = "Copyright (c) 2016 Cisco Systems, Inc."
__license__ = "MIT"
__version__ = "0.1.0"


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


# If the installation is on windows, place pyang.bat file in Scripts directory
if os.sep == '\\':
    script_dir = join(sys.prefix, 'Scripts')
    virltester_file = join(script_dir, 'virltester')
    path = join(script_dir, 'virltester.bat')
    with open(path, 'w') as script:
        script.write('@echo off\n%s %s %%*\n' % ('python', virltester_file))

setup(name='virltester',
      version=__version__,
      author=__author__,
      author_email=__author_email__,
      description="a VIRL automated test tool",
      long_description="An automated test tool which uses VIRL APIs to spin up simulations executes actions on simulations, records results and stops the simulation all based on a YAML formatted script.",
      url='https://github.com/rschmied/virltester',
      license='MIT',
      classifiers=[
            "Development Status :: 3 - Alpha",
            "Topic :: Utilities",
            "License :: OSI Approved :: BSD License",
            ],
      scripts=['bin/virltester'],
      packages=['virltester'],
      install_requires=read('requirements.txt')
      )

