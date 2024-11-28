# Variables
PYTHON := python3
VENV := venv
PIP := $(VENV)/bin/pip
PYTHON_VENV := $(VENV)/bin/python
PROJECT := src/gui/main_window.py
REQUIREMENTS := requirements.txt

# Default target
.DEFAULT_GOAL := help

# Help target
.PHONY: help
help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk '/^[a-zA-Z\-\_0-9]+:/ { \
		helpMessage = match(lastLine, /^## (.*)/); \
		if (helpMessage) { \
			helpCommand = substr($$1, 0, index($$1, ":")-1); \
			helpMessage = substr(lastLine, RSTART + 3, RLENGTH); \
			printf "  %-20s %s\n", helpCommand, helpMessage; \
		} \
	} \
	{ lastLine = $$0 }' $(MAKEFILE_LIST)
	@echo ''
	@echo 'Code Audit Commands:'
	@echo '  audit               Run full code audit and generate report'
	@echo '  audit-setup        Install dependencies for code auditing'
	@echo '  audit-report       View the latest audit report'
	@echo '  audit-clean        Remove audit reports'

# Core targets
.PHONY: install
install: verify-tcltk install-tkdnd ## Create virtual environment and install/update dependencies
	@echo "Creating virtual environment..."
	@$(PYTHON) -m venv $(VENV)
	@echo "Installing dependencies..."
	@$(PIP) install --upgrade pip
	@$(PIP) install -r $(REQUIREMENTS)
	@echo "Virtual environment created and dependencies installed."
	@echo "\033[0;32mActivate it with: source venv/bin/activate\033[0m"

.PHONY: run
run: ## Run the TV Show Renamer application
	@echo "Running TV Show Renamer..."
	@PYTHONPATH=. $(PYTHON_VENV) $(PROJECT)

.PHONY: clean
clean: ## Clean up environment and cached files
	@echo "Cleaning up..."
	@if [ -d "$(VENV)" ]; then \
		if [ -n "$$VIRTUAL_ENV" ]; then \
			echo "Deactivating virtual environment..."; \
			deactivate 2>/dev/null || true; \
		fi; \
		echo "Removing virtual environment..."; \
		rm -rf "$(VENV)"; \
	fi
	@if [ -d "tkdnd" ]; then \
		echo "Removing tkdnd directory..."; \
		rm -rf tkdnd; \
	fi
	@if command -v pip >/dev/null 2>&1; then \
		echo "Removing installed modules..."; \
		$(PYTHON) -m pip freeze 2>/dev/null | grep -v "^-e" | grep -v "^@" | xargs -r $(PYTHON) -m pip uninstall -y 2>/dev/null || true; \
	fi
	@echo "Removing cache files and directories..."
	@find . \( \
		-type d -name "__pycache__" -o \
		-type d -name "*.egg-info" -o \
		-type f -name "*.py[cod]" -o \
		-type f -name "*.so" -o \
		-type f -name "*.egg" -o \
		-type f -name ".DS_Store" -o \
		-type f -name ".coverage" -o \
		-type d -name ".pytest_cache" -o \
		-type d -name ".mypy_cache" -o \
		-type d -name ".coverage" -o \
		-type d -name "htmlcov" -o \
		-type d -name "build" -o \
		-type d -name "dist" \
	\) -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleanup complete."

# Code quality targets
.PHONY: lint
lint: ## Run code linting
	@echo "Running linting..."
	@$(PIP) install black pylint
	@$(VENV)/bin/black .
	@$(VENV)/bin/pylint src tests

.PHONY: test
test: ## Run tests
	@echo "Running tests..."
	@$(PYTHON_VENV) -m pytest tests/

# Environment setup targets
.PHONY: env-setup
env-setup: ## Create .env file from example
	@if [ ! -f .env ]; then \
		echo "Creating .env file from .env.example..."; \
		cp .env.example .env; \
		echo "Please update .env with your TMDb API key"; \
	else \
		echo ".env file already exists"; \
	fi

.PHONY: insert-api-key
insert-api-key: ## Insert TMDb API key into .env file
	@read -p "Enter your TMDb API key: " api_key; \
	if [ -z "$$api_key" ]; then \
		echo "API key cannot be empty"; \
		exit 1; \
	fi; \
	if [ ! -f .env ]; then \
		echo ".env file not found. Please run 'make env-setup' first."; \
		exit 1; \
	fi; \
	sed -i.bak "s/^TMDB_API_KEY=.*/TMDB_API_KEY=$$api_key/" .env; \
	echo "API key inserted into .env file."; \
	echo "" | pbcopy; \
	echo "Clipboard cleared."

.PHONY: update
update: ## Update all dependencies
	@echo "Updating dependencies..."
	@$(PIP) install --upgrade pip
	@$(PIP) install --upgrade -r $(REQUIREMENTS)

.PHONY: dev-setup
dev-setup: clean venv env-setup ## Setup development environment
	@echo "Development environment setup complete."
	@echo "Don't forget to:"
	@echo "1. Activate the virtual environment: source venv/bin/activate"
	@echo "2. Update the .env file with your TMDb API key"

# OS-specific configuration
ifeq ($(OS),Windows_NT)
    PYTHON := python
    VENV := venv
    PIP := $(VENV)\Scripts\pip
    PYTHON_VENV := $(VENV)\Scripts\python
else
    PYTHON := python3
    VENV := venv
    PIP := $(VENV)/bin/pip
    PYTHON_VENV := $(VENV)/bin/python
endif

# TkDnD installation targets
.PHONY: install-tkdnd
install-tkdnd: ## Install tkdnd for drag-and-drop support
	@echo "Installing tkdnd library..."
	@if ! command -v brew >/dev/null 2>&1; then \
		echo "Homebrew is required. Please install it first."; \
		exit 1; \
	fi
	@if ! brew list tcl-tk >/dev/null 2>&1; then \
		echo "Installing Tcl/Tk..."; \
		brew install tcl-tk; \
	fi
	@if ! command -v autoconf >/dev/null 2>&1; then \
		echo "Installing autoconf..."; \
		brew install autoconf automake libtool; \
	fi
	@TCL_PATH=$$(brew --prefix tcl-tk); \
	TCL_INCLUDE="$$TCL_PATH/include/tcl-tk"; \
	LOCAL_INSTALL_PATH="$$HOME/.local"; \
	echo "Using Tcl/Tk from: $$TCL_PATH"; \
	echo "Using Tcl/Tk headers from: $$TCL_INCLUDE"; \
	echo "Installing to: $$LOCAL_INSTALL_PATH"; \
	if [ ! -d "tkdnd" ]; then \
		echo "Cloning tkdnd repository..."; \
		git clone https://github.com/petasis/tkdnd.git && \
		cd tkdnd && \
		autoreconf -i && \
		./configure \
			--prefix="$$LOCAL_INSTALL_PATH" \
			--with-tcl="$$TCL_PATH/lib" \
			--with-tk="$$TCL_PATH/lib" \
			--with-tclinclude="$$TCL_INCLUDE" \
			--with-tkinclude="$$TCL_INCLUDE" && \
		make && \
		make install && \
		cd ..; \
	else \
		echo "tkdnd directory exists. Updating..."; \
		cd tkdnd && \
		git pull && \
		autoreconf -i && \
		./configure \
			--prefix="$$LOCAL_INSTALL_PATH" \
			--with-tcl="$$TCL_PATH/lib" \
			--with-tk="$$TCL_PATH/lib" \
			--with-tclinclude="$$TCL_INCLUDE" \
			--with-tkinclude="$$TCL_INCLUDE" && \
		make && \
		make install && \
		cd ..; \
	fi
	@echo "tkdnd installation completed."

.PHONY: verify-tcltk
verify-tcltk: ## Verify Tcl/Tk installation
	@echo "Verifying Tcl/Tk installation..."
	@TCL_PATH=$$(brew --prefix tcl-tk); \
	TCL_INCLUDE="$$TCL_PATH/include/tcl-tk"; \
	echo "Tcl/Tk path: $$TCL_PATH"; \
	echo "Tcl/Tk include path: $$TCL_INCLUDE"; \
	if [ ! -f "$$TCL_INCLUDE/tcl.h" ]; then \
		echo "tcl.h not found. Creating symlinks..."; \
		mkdir -p "$$TCL_INCLUDE"; \
		ln -sf "$$TCL_PATH/include/"*.h "$$TCL_INCLUDE/"; \
	fi; \
	echo "Tcl/Tk verification completed."

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