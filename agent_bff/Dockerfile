FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN python generate_proto.py

EXPOSE 8000

CMD ["gunicorn", "agent_bff.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4"]

