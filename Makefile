# Variables
APP_NAME = app.py
VENV_DIR = venv
PYTHON = $(VENV_DIR)/bin/python
PIP = $(VENV_DIR)/bin/pip

# Targets
.PHONY: all setup run test clean

all: setup run

setup:
	@echo "Setting up the virtual environment and installing dependencies..."
	python3 -m venv $(VENV_DIR)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run:
	@echo "Running the Flask application..."
	$(PYTHON) $(APP_NAME)

test:
	@echo "Running tests..."
	$(PYTHON) -m unittest discover -s tests

clean:
	@echo "Cleaning up..."
	rm -rf $(VENV_DIR)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete