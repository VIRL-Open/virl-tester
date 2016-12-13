from setuptools import setup, find_packages


__author__ = "Ralph Schmieder"
__author_email__ = "rschmied@cisco.com"
__copyright__ = "Copyright (c) 2016 Cisco Systems, Inc."
__license__ = "MIT"
__version__ = "0.1.1"


setup(name='virltester',
      version=__version__,
      author=__author__,
      author_email=__author_email__,
      description="a VIRL automated test tool",
      long_description="An automated test tool which uses VIRL APIs to spin up simulations executes actions on simulations, records results and stops the simulation all based on a YAML formatted script.",
      url='https://github.com/rschmied/virltester',
      license=__license__,
      platforms='Posix',
      classifiers=[
            "Development Status :: 3 - Alpha",
            "Topic :: Utilities",
            "License :: OSI Approved :: MIT License",
            ],
      entry_points={
          'console_scripts': [
              'virltester=virltester:main',
          ],
      },
      install_requires=[
          'paramiko>=2',
          'requests>=2',
          'PyYAML>=3'
      ],
      packages=find_packages(exclude=['Examples', 'test']),
      )

