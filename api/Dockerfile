FROM python:3.12-alpine
WORKDIR /app
COPY init_db.py server.py ./
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "server.py"]
