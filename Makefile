.PHONY: dev test lint docker

dev:
	flask run --port 5001 --debug

test:
	pytest tests/ -v

lint:
	ruff check .

docker:
	docker compose up --build
