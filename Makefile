.PHONY: check_all

check_all:
	poetry run ruff megamock tests
	poetry run mypy .
	poetry run pyright
