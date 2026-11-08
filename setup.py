"""Setuptools compatibility metadata for the optional Qt desktop interface."""

from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as handle:
    long_description = handle.read()

setup(
    name="monopolpy_companion",
    version="1.0.dev35",
    description="Electronic banker and GUI for physical Monopoly games",
    author="Taylor-Jayde Blackstone",
    author_email="t.blackstone@inspyre.tech",
    url="https://github.com/Inspyre-Softworks/monopolpy_companion",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    package_data={"monopolpy_companion.ui": ["resources/*.ttf", "resources/*-OFL.txt"]},
    python_requires=">=3.10",
    install_requires=["cryptography>=44,<47", "inspy-logger>=3.2.4,<4.0"],
    extras_require={
        "gui": ["PySide6>=6.8,<7"],
        "legacy-gui": [
            "PyYAML>=6,<7", "pysimplegui-4-foss>=4.60.4.1,<5",
            "colorlog>=6.10.1,<7",
        ],
    },
    entry_points={"console_scripts": ["monopolpy-companion=monopolpy_companion.cli:main"]},
    scripts=["monopolpy_companion.py"],
)
