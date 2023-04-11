.PHONY: check_all

check_all:
	poetry run flake8 megamock tests --max-complexity=10 --max-line-length=127
	poetry run mypy .
