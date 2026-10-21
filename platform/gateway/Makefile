.PHONY: install run gunicorn docker-build

PY ?= python3

install:
	pip install -r requirements.txt

# Run after the two module services are up (horse :8080, football :8081).
run:
	$(PY) -m app.main

gunicorn:
	gunicorn --bind 0.0.0.0:8000 --workers 2 --threads 4 app.wsgi:app

docker-build:
	docker build -t forekto-gateway .
