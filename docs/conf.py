"""Build the MonopolPy Companion documentation with Sphinx and Furo."""

from pathlib import Path
import tomllib


root = Path(__file__).resolve().parents[1]
with (root / "pyproject.toml").open("rb") as metadata:
    release = tomllib.load(metadata)["tool"]["poetry"]["version"]

project = "MonopolPy Companion"
author = "Inspyre-Softworks"
extensions = ["myst_parser", "sphinx_design", "sphinx_copybutton"]
exclude_patterns = ["_build"]
html_theme = "furo"
html_static_path = ["_static"]
html_css_files = ["custom.css"]

html_theme_options = {
    "navigation_with_keys": True,
    "source_repository": "https://github.com/Inspyre-Softworks/monopolpy_companion/",
    "source_branch": "master",
    "source_directory": "docs/",
    "light_css_variables": {
        "color-background-primary": "#fffef7",
        "color-background-secondary": "#f0f4ec",
        "color-background-border": "#d8e2d8",
        "color-foreground-primary": "#14271d",
        "color-foreground-secondary": "#476051",
        "color-brand-primary": "#176340",
        "color-brand-content": "#176340",
        "color-highlight-on-target": "#e0f1e3",
        "color-accent-red": "#bd2934",
    },
    "dark_css_variables": {
        "color-background-primary": "#101b18",
        "color-background-secondary": "#192824",
        "color-background-border": "#344c43",
        "color-foreground-primary": "#f7f6ef",
        "color-foreground-secondary": "#b6c9c0",
        "color-brand-primary": "#70d1a0",
        "color-brand-content": "#70d1a0",
        "color-highlight-on-target": "#2b5543",
        "color-accent-red": "#f05a60",
    },
}
