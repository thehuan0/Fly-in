.PHONY: all help install run debug clean lint lint-strict

VENV = venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip
FLAKE8 = $(VENV)/bin/flake8
MYPY = $(VENV)/bin/mypy


install:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install pydantic pygame rich mypy flake8

run:
	$(PYTHON) fly_in.py $(ARGS)

debug:
	$(PYTHON) -m pdb fly_in.py $(ARGS)

clean:
	rm -rf __pycache__ src/__pycache__ src/*/__pycache__ src/*/*/__pycache__ .mypy_cache
	rm -rf $(VENV)

lint:
	$(FLAKE8) src/ fly_in.py
	$(MYPY) --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs src/ fly_in.py

lint-strict:
	$(FLAKE8) src/ fly_in.py
	$(MYPY) --strict --ignore-missing-imports src/ fly_in.py