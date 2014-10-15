from setuptools import setup, find_packages


setup(name='pysparc',
      version='0.2',
      packages=find_packages(),
      url='http://github.com/hisparc/pysparc/',
      bugtrack_url='http://github.com/HiSPARC/pysparc/issues',
      license='GPLv3',
      author='David Fokkema, et al.',
      author_email='davidf@nikhef.nl',
      maintainer='HiSPARC',
      maintainer_email='beheer@hisparc.nl',
      description='Controlling HiSPARC hardware from python',
      long_description=open('README.rst').read(),
      keywords=['HiSPARC', 'Nikhef', 'cosmic rays'],
      classifiers=['Intended Audience :: Science/Research',
                   'Intended Audience :: Education',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python',
                   'Programming Language :: Python :: 2.7',
                   'Topic :: Scientific/Engineering',
                   'Topic :: Education',
                   'License :: OSI Approved :: GNU General Public License v3 (GPLv3)'],
      scripts=['bin/muonlab_with_http_api'],
      package_data={'pysparc': ['firmware.rbf', 'config.ini']},
      install_requires=[])
