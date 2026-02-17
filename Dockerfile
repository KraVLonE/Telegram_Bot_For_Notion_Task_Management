FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/

# Verify that main.py exists in src/ (or adjust import/cmd if module execution is preferred)
# We will run as a module: python -m src.main
CMD ["python", "-m", "src.main"]
