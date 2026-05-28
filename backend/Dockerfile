FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install -e ".[dev]"

# Install Chromium browser (image ships only headless-shell; we need full chromium for persistent context)
RUN python -m playwright install chromium --with-deps

COPY . .

EXPOSE 8080

CMD ["uvicorn", "dystore.main:app", "--host", "0.0.0.0", "--port", "8080"]
