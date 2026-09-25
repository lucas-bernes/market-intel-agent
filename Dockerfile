FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml constraints.txt ./
COPY src/ src/

# -c pins every package (and sub-dependency) to the versions the tests ran on.
RUN pip install --no-cache-dir -c constraints.txt .

EXPOSE 8000

CMD ["uvicorn", "market_intel.api:app", "--host", "0.0.0.0", "--port", "8000"]
