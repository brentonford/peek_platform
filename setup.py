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
    "Cython >= 0.21.1",
    "GeoAlchemy2",
    "GitPython >= 2.0.8",
    "Pygments >= 2.0.1",
    "SQLAlchemy >= 1.0.14",
    "SQLAlchemy-Utils >= 0.32.9",
    "Shapely >= 1.5.16",
    "Sphinx >= 1.4.8",
    "Twisted[tls,conch,soap] >= 16.0.0",
    "alembic >= 0.8.7",
    "amqp >= 1.4.9",
    "celery[redis,auth]",
    "vine",
    "git+https://github.com/celery/py-amqp#egg=amqp",
    "dxfgrabber >= 0.7.4",
    "flower",
    "gitdb",
    "jira",
    "kwonly-args",
    "lxml >= 3.6.4",
    "psycopg2 >= 2.6.2",
    "pyOpenSSL >= 16.2.0",
    "pyasn1 >= 0.1.9",
    "pyasn1-modules >= 0.0.8",
    "pycrypto >= 2.6.1",
    "python-dateutil >= 2.6.0",
    "redis >= 2.10.5",
    "service-identity >= 16.0.0",
    # Synerty packages
    "pydirectory >= 0.1.9",
    "txhttputil >= 0.1.5",
    "vort"
]

dev_requirements = [
    "coverage==4.2",
    "mock==2.0.0",
    "selenium==2.53.6",

]

setup(
    name=package_name,
    packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    install_requires=requirements,
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
