from setuptools import setup, find_packages


__author__ = "Ralph Schmieder"
__author_email__ = "rschmied@cisco.com"
__copyright__ = "Copyright (c) 2017 Cisco Systems, Inc."
__license__ = "MIT"
__version__ = "0.3.0"


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
          'jinja2>=2',
          'netaddr>=0.7'
          'paramiko>=2.1,<2.2',
          'paramiko-expect>=0.2',
          'requests>=2',
          'PyYAML>=3'
      ],
      packages=find_packages(exclude=['Examples', 'test']),
      )

