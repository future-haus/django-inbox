test:
	docker compose run --rm inbox-django-5 python runtests.py

init-db:
	docker compose run -e "PGPASSWORD=password" --rm db psql -h db -U inbox -d inbox -f /app/init.sql
