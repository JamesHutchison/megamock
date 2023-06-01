#!/usr/bin/env bash

export PTYME_WATCHED_DIRS=.:./.devcontainer:./.vscode:./.github
poetry run ptyme-track --standalone
