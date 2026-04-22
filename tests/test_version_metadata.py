import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def extract_version(path: Path, pattern: str) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(pattern, text, re.MULTILINE)
    if match is None:
        raise AssertionError(f"Could not find version in {path}")
    return match.group(1)


class VersionMetadataTests(unittest.TestCase):
    def test_pyproject_and_setup_versions_match(self) -> None:
        pyproject_version = extract_version(ROOT / "pyproject.toml", r'^version\s*=\s*"([^"]+)"')
        setup_version = extract_version(ROOT / "setup.py", r'version\s*=\s*"([^"]+)"')
        self.assertEqual(pyproject_version, setup_version)


if __name__ == "__main__":
    unittest.main()
