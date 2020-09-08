from setuptools import setup, find_packages
import os

version = '1.2.0'

tests_require = [
    'ftw.testing',
    'ftw.testbrowser',
    'plone.app.testing',
    'plone.testing',
]

extras_require = {
    'tests': tests_require,
}


setup(
    name='ftw.monitor',
    version=version,
    description='ftw.monitor',
    long_description=open('README.rst').read() + '\n' + open(
        os.path.join('docs', 'HISTORY.txt')).read(),

    # Get more strings from
    # http://www.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Framework :: Plone',
        'Framework :: Plone :: 4.3',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],

    keywords='ftw monitor',
    author='4teamwork AG',
    author_email='mailto:info@4teamwork.ch',
    url='https://github.com/4teamwork/ftw.monitor',
    license='GPL2',

    packages=find_packages(exclude=['ez_setup']),
    namespace_packages=['ftw'],
    include_package_data=True,
    zip_safe=False,

    install_requires=[
        'Plone',
        'setuptools',
        'plone.api',
        'psutil',
        'requests',
        'zc.monitor',
        'zc.z3monitor',
        'ZODB3',
        'zope.component',
        'zope.processlifetime'
    ],

    tests_require=tests_require,
    extras_require=extras_require,

    entry_points="""
    # -*- Entry points: -*-
    [z3c.autoinclude.plugin]
    target = plone

    [plone.recipe.zope2instance.ctl]
    monitor = ftw.monitor.command:monitor

    [console_scripts]
    dump-perf-metrics = ftw.monitor.command:dump_perf_metrics
    """,
)
