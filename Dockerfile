FROM python:3.13-slim

# Libraries WeasyPrint needs for PDF output, and a font that includes Hebrew.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpango-1.0-0 libpangoft2-1.0-0 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN DEBUG=0 SECRET_KEY=build python manage.py collectstatic --noinput

ENV DEBUG=0
EXPOSE 8000
# The timeout is generous because a PDF with hundreds of pages takes a while to render;
# threads keep the site responsive for everyone else in the meantime.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py ensure_admin && gunicorn config.wsgi --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} --threads 4 --timeout 300"]
