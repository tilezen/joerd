from setuptools import setup, find_packages

version = '0.0.1'

setup(name='joerd',
      version=version,
      description="A tool for downloading and generating elevation data.",
      long_description=open('README.md').read(),
      classifiers=[
          # strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: MIT License',
          'Natural Language :: English',
          'Operating System :: POSIX :: Linux',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: Implementation :: CPython',
          'Topic :: Scientific/Engineering :: GIS',
          'Topic :: Utilities',
      ],
      keywords='map dem elevation raster',
      author='Matt Amos, Mapzen',
      author_email='matt.amos@mapzen.com',
      url='https://github.com/mapzen/joerd',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'GDAL',
          'beautifulsoup4',
          'requests',
          'numpy',
          'PyYAML',
          'pyqtree',
          'geographiclib',
          'boto3',
          'contextlib2',
      ],
      test_suite='tests',
      tests_require=[
          'httptestserver',
      ],
      entry_points=dict(
          console_scripts=[
              'joerd = joerd.command:joerd_main',
          ]
      )
)
