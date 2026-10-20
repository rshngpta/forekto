.PHONY: venv install sample-data train run gunicorn test lint docker-build clean

PY ?= python3

venv:
	$(PY) -m venv .venv
	@echo "Activate with: source .venv/bin/activate"

install:
	pip install -r requirements.txt

sample-data:
	$(PY) ml/make_sample_data.py

train:
	$(PY) ml/train.py

run:
	$(PY) -m app.main

gunicorn:
	gunicorn --bind 0.0.0.0:8080 --workers 2 --threads 4 app.wsgi:app

test:
	pytest -q

lint:
	flake8 app ml tests --max-line-length=100

docker-build:
	docker build -t forekto-horse-racing .

clean:
	rm -rf model/*.pkl model/metadata.json data/*.csv __pycache__ .pytest_cache
