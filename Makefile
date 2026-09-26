PYTHON ?= python3
PORT ?= 8765

.PHONY: check test preview release viewer

check:
	$(PYTHON) tools/project.py check

test:
	$(PYTHON) -m unittest discover -s tests -v

preview: check test
	$(PYTHON) tools/project.py package

release: test
	$(PYTHON) tools/project.py package --release

viewer:
	$(PYTHON) tools/viewer.py --port $(PORT)
