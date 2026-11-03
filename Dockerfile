# Stage 1: Build dependencies and train the model
FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements-serving.txt .
RUN pip install --no-cache-dir --user -r requirements-serving.txt

COPY data/processed/iris_features.csv data/processed/iris_features.csv
COPY src/train_final_model.py src/train_final_model.py

RUN mkdir -p models && python src/train_final_model.py


# Stage 2: Minimal runtime image
FROM python:3.11-slim AS runtime

WORKDIR /app

COPY --from=builder /root/.local /root/.local
COPY --from=builder /build/models/ models/
COPY src/serve.py src/serve.py

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["python", "src/serve.py"]
