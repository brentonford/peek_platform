import os
import shutil
from distutils.core import setup

from setuptools import find_packages

package_name = "peek_platform"
package_version = "0.0.0"

egg_info = "%s.egg-info" % package_name
if os.path.isdir(egg_info):
    shutil.rmtree(egg_info)



setup(
    name=package_name,
    packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    version=package_version,
    description='Peek Platform Common Code',
    author='Synerty',
    author_email='contact@synerty.com',
    url='https://github.com/Synerty/%s' % package_version,
    download_url='https://github.com/Synerty/%s/tarball/%s' % (
    package_name, package_version),
    keywords=['Peek', 'Python', 'Platform', 'synerty'],
    classifiers=[],
)
