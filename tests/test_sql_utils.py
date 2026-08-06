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
"""Tests for audioanalyser.modules.sql_utils."""

import sqlite3

import pytest

from audioanalyser.modules.sql_utils import (
    MAX_IDENTIFIER_LENGTH,
    safe_identifier,
)


class TestAcceptedIdentifiers:
    @pytest.mark.parametrize(
        "name",
        [
            "analysis",
            "transcripts",
            "translations",
            "recommendations",
            "table_1",
            "_private",
            "A" * MAX_IDENTIFIER_LENGTH,
        ],
    )
    def test_accepts_the_names_this_package_uses(self, name):
        assert safe_identifier(name) == name


class TestRejectedIdentifiers:
    @pytest.mark.parametrize(
        "name",
        [
            "",
            None,
            123,
            "1_starts_with_a_digit",
            "has space",
            "has-hyphen",
            "A" * (MAX_IDENTIFIER_LENGTH + 1),
        ],
    )
    def test_rejects_malformed_names(self, name):
        with pytest.raises(ValueError):
            safe_identifier(name)

    @pytest.mark.parametrize(
        "payload",
        [
            "t; DROP TABLE users",
            "t--",
            "t/*comment*/",
            'analysis" ; DELETE FROM analysis; --',
            "analysis') OR ('1'='1",
            "t\nUNION SELECT 1",
        ],
    )
    def test_rejects_statement_breaking_payloads(self, payload):
        """Every character needed to escape the statement is excluded."""
        with pytest.raises(ValueError, match="letters, digits"):
            safe_identifier(payload)


class TestAgainstRealSqlite:
    def test_a_rejected_name_would_have_executed_extra_statements(
        self, tmp_path
    ):
        """Shows the injection is real, not theoretical.

        executescript runs the payload the way an unvalidated f-string
        interpolation into a multi-statement execution would.
        """
        db = tmp_path / "probe.db"
        payload = "t (x TEXT); DROP TABLE victim; --"

        with sqlite3.connect(db) as conn:
            conn.executescript("CREATE TABLE victim (x TEXT)")
            conn.executescript(f"CREATE TABLE {payload}")
            remaining = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()

        assert ("victim",) not in remaining, "the payload dropped the table"

        # The validator refuses that same name.
        with pytest.raises(ValueError):
            safe_identifier(payload)

    def test_an_accepted_name_creates_exactly_one_table(self, tmp_path):
        db = tmp_path / "ok.db"
        name = safe_identifier("analysis")

        with sqlite3.connect(db) as conn:
            conn.executescript(f"CREATE TABLE {name} (x TEXT)")
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()

        assert tables == [("analysis",)]
