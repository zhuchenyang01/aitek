FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV HOST=0.0.0.0
ENV PORT=8002

EXPOSE 8002
CMD ["python", "wsgi.py"]
