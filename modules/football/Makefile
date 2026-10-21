.PHONY: install sample-data train seed run gunicorn test lint docker-build clean

PY ?= python3

install:
	pip install -r requirements.txt

sample-data:
	$(PY) ml/make_sample_data.py

train:
	$(PY) ml/train.py

seed:
	$(PY) ml/seed_predictions.py

run:
	$(PY) -m app.main

gunicorn:
	gunicorn --bind 0.0.0.0:8081 --workers 2 --threads 4 app.wsgi:app

test:
	pytest -q

lint:
	flake8 app ml tests --max-line-length=100

docker-build:
	docker build -t forekto-football .

clean:
	rm -rf model/*.pkl model/metadata.json data/*.csv data/*.db __pycache__ .pytest_cache
