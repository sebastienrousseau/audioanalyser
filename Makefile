# Basic Makefile for AudioAnalyser Application

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
#
# See the License for the specific language governing permissions and
# limitations under the License.

.PHONY: install run clean

install:
    pip install -r requirements.txt

run:
    python -m audioanalyser

clean:
    rm -rf __pycache__
    rm -rf build/
    rm -rf dist/
    rm -rf *.egg-info
