FROM python:3.12-slim

RUN useradd --create-home --uid 10001 appuser
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY data ./data
COPY gunicorn.conf.py .

RUN chown -R appuser:appuser /app
USER appuser

ENV APP_ENV=development
EXPOSE 5001

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5001/ready')"

# Override CMD for production: gunicorn -c gunicorn.conf.py app.main:app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5001"]
