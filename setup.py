#!/usr/bin/env python

from setuptools import setup

setup(
    use_scm_version={
        "local_scheme": "no-local-version",
        "write_to": "py7zr/version.py",
        "write_to_template": '__version__ = "{version}"\n',
        "tag_regex": r"^(?P<prefix>v)?(?P<version>[^\+]+)(?P<suffix>.*)?$",
    }
)
