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
"""Helpers for building SQL safely.

SQLite cannot parameterise identifiers, so table names have to be
interpolated into the statement text. Every table name in this package comes
from an environment variable, which makes that interpolation an injection
point: a crafted ANALYSIS_DB_TABLE_NAME would otherwise be executed verbatim.
Validating the identifier closes it without changing how the tables are named.
"""

import re

# Matches an unquoted SQL identifier: a letter or underscore, then letters,
# digits or underscores. Deliberately stricter than SQLite accepts - it is the
# set of names this package actually uses.
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

MAX_IDENTIFIER_LENGTH = 64


def safe_identifier(name):
    """Return ``name`` if it is safe to interpolate into a statement.

    Args:
        name: The proposed table or column name.

    Returns:
        str: The validated identifier, unchanged.

    Raises:
        ValueError: If the name is empty, over-long, or contains anything
            outside ``[A-Za-z0-9_]`` - which includes every character needed
            to break out of the statement (quotes, semicolons, whitespace).
    """
    if not name or not isinstance(name, str):
        raise ValueError(
            f"SQL identifier must be a non-empty string: {name!r}"
        )

    if len(name) > MAX_IDENTIFIER_LENGTH:
        raise ValueError(
            f"SQL identifier is longer than {MAX_IDENTIFIER_LENGTH} "
            f"characters: {name!r}"
        )

    if not _IDENTIFIER.match(name):
        raise ValueError(
            f"SQL identifier may contain only letters, digits and "
            f"underscores, and may not start with a digit: {name!r}"
        )

    return name
