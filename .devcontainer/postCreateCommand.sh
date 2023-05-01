#!/usr/bin/env bash

# git config that should be default
git config --global pull.rebase true
git config --global fetch.prune true
git config --global diff.colorMoved zebra
git config --global rebase.autoStash true

pip install poetry

poetry config virtualenvs.in-project true
poetry install

# install rust
curl https://sh.rustup.rs -sSf | sh -s -- -y
