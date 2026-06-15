"""Backward-compatible setup.py for older pip versions.

This file exists to support `pip install -e .` on pip < 21.3.
All configuration is in pyproject.toml.
"""
from setuptools import setup

if __name__ == "__main__":
    setup()
