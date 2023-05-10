#!/usr/bin/env bash

sudo chown vscode:vscode ./.venv
sudo chown vscode:vscode ./tests/perf/generated_modules
sudo chown vscode:vscode ./.mypy_cache
sudo chown vscode:vscode ./.pytest_cache

# git config that should be default
git config --global pull.rebase true
git config --global fetch.prune true
git config --global diff.colorMoved zebra
git config --global rebase.autoStash true

pip install poetry

poetry config virtualenvs.in-project true
poetry install

python tests/perf/generate_files_to_import.py
