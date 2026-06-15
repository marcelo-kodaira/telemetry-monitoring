FROM python:3.12-slim
WORKDIR /app
# Copy the source before installing — the editable install needs the `app` package present.
COPY . .
RUN pip install --no-cache-dir -e ".[dev]"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
