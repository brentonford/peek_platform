import os
import shutil
from distutils.core import setup

from setuptools import find_packages

package_name = "peek_platform"
package_version = "0.0.0"

egg_info = "%s.egg-info" % package_name
if os.path.isdir(egg_info):
    shutil.rmtree(egg_info)

requirements = [
    # networking and async framework. Peek is based on Twisted.
    "Cython >= 0.21.1",
    "Twisted[tls,conch,soap] >= 16.0.0",
    "pyOpenSSL >= 16.2.0",
    "pyasn1 >= 0.1.9",
    "pyasn1-modules >= 0.0.8",

    # Database
    "psycopg2 >= 2.6.2",  # PostGreSQL for Linux
    "GeoAlchemy2",  # Geospatial addons to SQLAlchemy
    "Shapely >= 1.5.16",  # Geospatial shape manipulation
    "SQLAlchemy >= 1.0.14",  # Database abstraction layer
    "SQLAlchemy-Utils >= 0.32.9",
    "alembic >= 0.8.7",  # Database migration utility

    # Utilities
    "python-dateutil >= 2.6.0",
    "Pygments >= 2.0.1",  # Generate HTML for code that is syntax styled

    # Celery packages
    "flower",
    # "amqp >= 1.4.9",  # DEPENDENCY LINK BELOW
    "celery[redis,auth]",
    "redis >= 2.10.5",

    # Potitially useful packages
    "GitPython >= 2.0.8",
    "jira",
    "lxml >= 3.6.4",
    "dxfgrabber >= 0.7.4",

    # Synerty packages
    "pytmpdir >= 0.1.0",  # A temporary directoy, usefull for extracting archives to
    "txhttputil >= 0.1.6",  # Utility class for http requests
    "vortexpy >= 0.1.4",  # Data serialisation and transport layer, observable based
    "json-cfg",  # DEPENDENCY LINK BELOW
    "kwonly-args",  # Required for json-cfg
    "txsuds-py3",  # DEPENDENCY LINK BELOW

    # Peek platform dependencies, all must match
    "papp_base", ##==%s" % package_version,
]

# Packages that are presently installed from a git repo
dependency_links = [
    # Celery packages
    # "git+https://github.com/celery/py-amqp#egg=amqp",

    # Synerty packages
    "https://github.com/Synerty/json-cfg/tarball/master#egg=json-cfg-0.5.0",  # The file config utility
    "https://github.com/Synerty/txsuds-py3/tarball/master#egg=txsuds-py3-0.0.0",  # The soap client
]

dev_requirements = [
    "coverage >= 4.2",
    "mock >= 2.0.0",
    "selenium >= 2.53.6",
    "Sphinx >= 1.4.8",
]

setup(
    name=package_name,
    packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    install_requires=requirements,
    dependency_links=dependency_links,
    version=package_version,
    description='Peek Platform Common Code',
    author='Synerty',
    author_email='contact@synerty.com',
    url='https://github.com/Synerty/%s' % package_version,
    download_url='https://github.com/Synerty/%s/tarball/%s' % (
        package_name, package_version),
    keywords=['Peek', 'Python', 'Platform', 'synerty'],
    classifiers=[
        "Programming Language :: Python :: 3.5",
    ],
)