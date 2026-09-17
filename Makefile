.PHONY: data analyze web all clean install

PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip

install:
	python3 -m venv .venv
	$(PIP) install -r requirements.txt
	cd web && npm install

data:
	$(PYTHON) scripts/download_detroit_data.py
	$(PYTHON) scripts/download_census_data.py
	$(PYTHON) scripts/download_grocery_candidates.py

analyze: data
	$(PYTHON) scripts/build_walk_network.py
	$(PYTHON) scripts/calculate_accessibility.py
	$(PYTHON) scripts/export_web_data.py

web:
	cd web && npm run dev

all: analyze
	@echo "Open the web app with: make web"

clean:
	rm -rf data/raw/* data/processed/* outputs/*
	mkdir -p data/raw data/processed data/manual outputs
