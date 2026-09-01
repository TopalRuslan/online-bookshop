FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

EXPOSE 8000

# Migrations are NOT run here — they belong to a dedicated step (the `migrate`
# service in docker-compose.yml, a Job in k8s) so they run exactly once and
# not on every replica / restart.
CMD ["gunicorn", "proj.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
