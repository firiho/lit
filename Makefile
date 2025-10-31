.PHONY: help install install-dev test test-cov clean format lint type-check run build publish

help:
	@echo "Lit - Development Commands"
	@echo "==============================="
	@echo "install        - Install package"
	@echo "install-dev    - Install package with dev dependencies"
	@echo "test           - Run tests"
	@echo "test-cov       - Run tests with coverage"
	@echo "clean          - Clean build artifacts"
	@echo "format         - Format code with black"
	@echo "lint           - Lint code with flake8"
	@echo "type-check     - Type check with mypy"
	@echo "run            - Run lit CLI"
	@echo "build          - Build distribution packages"
	@echo "publish        - Publish to PyPI (requires credentials)"
	@echo "publish-test   - Publish to TestPyPI (for testing)"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test:
	python -m pytest -q --tb=no

test-cov:
	python -m pytest --cov=lit --cov-report=html --cov-report=term-missing

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf tmp/
	rm -rf test-*/
	rm -f .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".lit" -exec rm -rf {} +

format:
	black lit/ tests/

lint:
	flake8 lit/ tests/ --max-line-length=88 --extend-ignore=E203,W503

type-check:
	mypy lit/

run:
	python -m lit

build:
	python -m build

publish-test:
	python -m twine upload --repository testpypi dist/*

publish:
	python -m twine upload dist/*
