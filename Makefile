PYTHON ?= python3

.PHONY: check test preview release

check:
	$(PYTHON) tools/project.py check

test:
	$(PYTHON) -m unittest discover -s tests -v

preview: check test
	$(PYTHON) tools/project.py package

release: test
	$(PYTHON) tools/project.py package --release
