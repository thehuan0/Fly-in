VENV = venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip

MAIN_FILE = fly_in.py
CONFIG_FILE = config.txt
SRC_FILES = a_maze_ing.py config/ mazegen/ display.py

all: install run

install: $(VENV)/bin/activate

$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	@$(PIP) install --upgrade pip
	@$(PIP) install -r requirements.txt
	@$(PIP) install -e .
	@touch $(VENV)/bin/activate

run:
	$(PYTHON) $(MAIN_FILE) $(CONFIG_FILE)

debug:
	$(PYTHON) -m pdb $(MAIN_FILE) $(CONFIG_FILE)

lint:
	@$(PYTHON) -m flake8 $(SRC_FILES)
	@$(PYTHON) -m mypy $(SRC_FILES) \
		--exclude "mlx/.*" \
		--follow-imports=skip \
		--warn-return-any \
		--warn-unused-ignores \
		--ignore-missing-imports \
		--disallow-untyped-defs \
		--check-untyped-defs

lint-strict:
	@$(PYTHON) -m flake8 $(SRC_FILES)
	@$(PYTHON) -m mypy $(SRC_FILES) \
		--strict \
		--exclude "mlx/.*" \
		--follow-imports=skip

package: install
	@$(PYTHON) -m build

clean:
	@rm -rf __pycache__ .mypy_cache $(VENV) build dist *.egg-info
	@find . -type d -name "__pycache__" -exec rm -rf {} +

.PHONY: all lint clean run debug package