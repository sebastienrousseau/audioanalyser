# Copyright (C) 2023-2024 Sebastien Rousseau.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Guards against drift between the packaging manifests.

The version and the supported Python floor are each declared in more than
one file, and nothing else checks that they agree. The release workflow
reads only setup.cfg, so a pyproject-only bump would publish under the old
version without any step failing.
"""

import configparser
import pathlib
import re

import audioanalyser

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _pyproject_value(section, key):
    """Read one scalar from a pyproject section.

    Deliberately not tomllib: that is 3.11+, and this package supports 3.10.
    Only two scalars are needed, so a section-aware scan avoids adding a
    backport dependency just for the tests.
    """
    text = (ROOT / "pyproject.toml").read_text()
    current = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current = stripped[1:-1]
            continue
        if current != section:
            continue
        match = re.match(rf'{re.escape(key)}\s*=\s*"([^"]+)"', stripped)
        if match:
            return match.group(1)
    raise AssertionError(f"{key} not found in [{section}]")


def _setup_cfg():
    parser = configparser.ConfigParser()
    parser.read(ROOT / "setup.cfg")
    return parser


def _setup_py():
    return (ROOT / "setup.py").read_text()


class TestVersionAgreement:
    def test_setup_cfg_and_pyproject_declare_the_same_version(self):
        """The release job reads setup.cfg; poetry builds from pyproject."""
        assert _setup_cfg()["metadata"]["version"] == _pyproject_value(
            "tool.poetry", "version"
        )

    def test_the_package_reports_that_version_too(self):
        assert audioanalyser.__version__ == _setup_cfg()["metadata"]["version"]


class TestPythonFloorAgreement:
    def test_setup_py_and_pyproject_declare_the_same_floor(self):
        declared = re.search(
            r"python_requires\s*=\s*'>=([0-9.]+)'", _setup_py()
        )
        assert declared, "setup.py declares no python_requires"

        poetry = _pyproject_value("tool.poetry.dependencies", "python")
        assert poetry.lstrip("^~>=") == declared.group(1)

    def test_the_classifiers_do_not_advertise_an_unsupported_version(self):
        """A classifier for a version below the floor invites bug reports."""
        floor = tuple(
            int(part)
            for part in _pyproject_value(
                "tool.poetry.dependencies", "python"
            )
            .lstrip("^~>=")
            .split(".")
        )
        advertised = re.findall(
            r"'Programming Language :: Python :: ([0-9]+\.[0-9]+)'",
            _setup_py(),
        )

        assert advertised, "setup.py advertises no Python versions"
        for version in advertised:
            parts = tuple(int(part) for part in version.split("."))
            assert parts >= floor, (
                f"classifier advertises Python {version}, below the "
                f"declared floor {'.'.join(str(p) for p in floor)}"
            )
