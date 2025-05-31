# Variables (auto-detect platform)
ifeq ($(OS),Windows_NT)
	PYTHON = python
	VENV = venv
	PIP = $(VENV)\Scripts\pip
	PYTHON_VENV = $(VENV)\Scripts\python
else
	PYTHON = python3
	VENV = venv
	PIP = $(VENV)/bin/pip
	PYTHON_VENV = $(VENV)/bin/python
endif
PROJECT = src/gui/main_window.py
REQUIREMENTS = requirements.txt
.DEFAULT_GOAL := help

# Default target
.DEFAULT_GOAL := help

# Help target
.PHONY: help
help:
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Common targets:'
	@echo '  install        Setup all dependencies'
	@echo '  run            Run the application'
	@echo '  clean          Remove build artifacts and venv'
	@echo '  lint           Run code linting'
	@echo '  test           Run tests'
	@echo '  update         Update all dependencies'
	@echo '  dev-setup      Setup development environment'
	@echo '  env-setup      Create .env file from example'
	@echo '  insert-api-key Insert TMDb API key into .env'
	@echo ''
	@echo 'See Makefile for all targets.'

# Core targets
.PHONY: install
install: venv verify-tcltk install-tkdnd ## Setup all dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -r $(REQUIREMENTS)
	@echo "\033[0;32mActivate: source venv/bin/activate\033[0m"

.PHONY: run
run:
	PYTHONPATH=. $(PYTHON_VENV) $(PROJECT)

.PHONY: clean
clean:
	rm -rf $(VENV) tkdnd
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.py[cod]" -delete 2>/dev/null || true
	find . -type f -name "*.so" -delete 2>/dev/null || true
	find . -type f -name "*.egg" -delete 2>/dev/null || true
	find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true

# Code quality targets
.PHONY: lint
lint:
	$(PIP) install black pylint
	$(VENV)/bin/black .
	$(VENV)/bin/pylint src tests

.PHONY: test
test:
	$(PYTHON_VENV) -m pytest tests/

# Environment setup targets
.PHONY: env-setup
env-setup:
	@if [ ! -f .env ]; then cp .env.example .env && echo "Created .env from .env.example. Please update your TMDb API key."; else echo ".env already exists"; fi

.PHONY: insert-api-key
insert-api-key:
	@read -p "Enter your TMDb API key: " api_key; \
	[ -z "$$api_key" ] && echo "API key cannot be empty" && exit 1; \
	[ ! -f .env ] && echo ".env file not found. Run 'make env-setup' first." && exit 1; \
	sed -i.bak "s/^TMDB_API_KEY=.*/TMDB_API_KEY=$$api_key/" .env && echo "API key inserted into .env." && echo "" | pbcopy && echo "Clipboard cleared."

.PHONY: update
update:
	$(PIP) install --upgrade pip
	$(PIP) install --upgrade -r $(REQUIREMENTS)

.PHONY: dev-setup
dev-setup: clean env-setup
	@echo "Development environment setup complete."
	@echo "Activate: source venv/bin/activate"
	@echo "Update .env with your TMDb API key"

# Add venv target
.PHONY: venv
venv:
	@if [ ! -d $(VENV) ]; then $(PYTHON) -m venv $(VENV); fi

# TkDnD installation targets
.PHONY: install-tkdnd
install-tkdnd:
	@if ! command -v brew >/dev/null 2>&1; then echo "Homebrew required"; exit 1; fi
	@if ! brew list tcl-tk >/dev/null 2>&1; then brew install tcl-tk; fi
	@if ! command -v autoconf >/dev/null 2>&1; then brew install autoconf automake libtool; fi
	@TCL_PATH=$$(brew --prefix tcl-tk); TCL_INCLUDE="$$TCL_PATH/include/tcl-tk"; LOCAL_INSTALL_PATH="$$HOME/.local"; \
	if [ ! -d "tkdnd" ]; then \
		git clone https://github.com/petasis/tkdnd.git || exit 1; \
		cd tkdnd && autoreconf -i && ./configure --prefix="$$LOCAL_INSTALL_PATH" --with-tcl="$$TCL_PATH/lib" --with-tk="$$TCL_PATH/lib" --with-tclinclude="$$TCL_INCLUDE" --with-tkinclude="$$TCL_INCLUDE"; \
		cd ..; \
	fi; \
	make -C tkdnd && make -C tkdnd install

.PHONY: verify-tcltk
verify-tcltk:
	@TCL_PATH=$$(brew --prefix tcl-tk); TCL_INCLUDE="$$TCL_PATH/include/tcl-tk"; \
	[ ! -f "$$TCL_INCLUDE/tcl.h" ] && mkdir -p "$$TCL_INCLUDE" && ln -sf "$$TCL_PATH/include/"*.h "$$TCL_INCLUDE/"; \
	echo "Tcl/Tk path: $$TCL_PATH"; echo "Tcl/Tk include path: $$TCL_INCLUDE"; echo "Tcl/Tk verification completed."

# Code audit targets
.PHONY: audit audit-setup audit-report audit-clean

audit-setup: ## Setup code audit environment
	@echo "Setting up code audit environment..."
	@$(PIP) install astroid pylint difflib

audit: audit-setup ## Run full code audit
	@echo "Running code audit..."
	@mkdir -p reports
	@$(PYTHON_VENV) tools/code_auditor.py $(CURDIR) > reports/audit_report.txt
	@echo "Audit report generated at reports/audit_report.txt"

audit-report: ## View latest audit report
	@if [ -f reports/audit_report.txt ]; then \
		cat reports/audit_report.txt; \
	else \
		echo "No audit report found. Run 'make audit' first."; \
	fi

audit-clean: ## Remove audit reports
	@echo "Cleaning audit reports..."
	@rm -rf reports/audit_report.txt