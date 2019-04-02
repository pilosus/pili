.DEFAULT_GOAL := lint

.PHONY: install
install:
	pip install -U setuptools pip
	pip install -U -r requirements.txt
	pip install -e .

.PHONY: format
format:
	isort -rc -w 88 pili tests
	black -S -l 88 --target-version py36 pili tests

.PHONY: lint
lint:
	python setup.py check -rms
	flake8 pili/ pili/
	black -S -l 88 --target-version py36 --check pili tests

.PHONY: mypy
mypy:
	mypy pili


.PHONY: clean
clean:
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]' `
	rm -f `find . -type f -name '*~' `
	rm -f `find . -type f -name '.*~' `
	rm -rf .cache
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf htmlcov
	rm -rf *.egg-info
	rm -f .coverage
	rm -f .coverage.*
	rm -rf build
	python setup.py clean

