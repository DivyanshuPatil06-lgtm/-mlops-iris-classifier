# Practical 10: Docker Containerization of the Iris ML Application

## 1. Objective

To containerize the Iris machine learning application using Docker, package a trained model, expose HTTP endpoints for predictions, and verify the application using health checks.

## 2. Tools and Technologies

- Docker Desktop with the Linux container engine (WSL 2 backend)
- Python 3.11 (python:3.11-slim base image)
- scikit-learn 1.5.1, pandas 2.2.2, NumPy 1.26.4, joblib 1.4.2
- Python built-in http.server
- Git and GitHub

## 3. Implementation

The application uses a multi-stage Dockerfile.

### Builder stage

- Installs the pinned Python dependencies from requirements-serving.txt.
- Copies data/processed/iris_features.csv and src/train_final_model.py.
- Trains a Random Forest classifier and saves the model and label encoder to models/.

### Runtime stage

- Starts again from a clean python:3.11-slim image.
- Copies only the installed Python packages and the trained models/ folder from the builder.
- Copies src/serve.py.
- Exposes port 8000 and configures a Docker health check on /health.

### Why a multi-stage build

Training data, the training script and anything used only during the build stay in the builder stage and never reach the final image. This keeps the deployed image limited to what is needed for serving, and it reduces the attack surface. Requirements are copied and installed before the source files so Docker can cache the slow pip install layer.

## 4. HTTP Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | /health | Checks application health |
| POST | /predict | Predicts an Iris species from the required features |

The prediction request contains four original Iris measurements and three engineered numeric features: sepal_area, petal_area, and sepal_to_petal_length_ratio.

## 5. Health Check Configuration

The Dockerfile defines:

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3

The check runs a short Python command inside the container that requests http://localhost:8000/health. Docker marks the container healthy when the request succeeds and unhealthy after 3 consecutive failures. In testing, docker ps showed the container as (healthy) about 30 seconds after start.

## 6. Build and Run

Build the image:

docker build -t iris-classifier:v1 .

Start the container:

docker run -d --name iris-classifier-container -p 8000:8000 iris-classifier:v1

Check container status:

docker ps

## 7. Testing and Results

### Health check

Request: curl http://localhost:8000/health

Observed response: {"status": "healthy"}

### Valid prediction

For the sample Iris measurements (5.1, 3.5, 1.4, 0.2 plus the engineered features), the application returned:

{"prediction": "setosa", "probabilities": [1.0, 0.0, 0.0]}

### Invalid request

A request containing only one feature returned HTTP 400 Bad Request and listed the six missing fields:

{"error": "Missing features", "missing": ["sepal width (cm)", "petal length (cm)", "petal width (cm)", "sepal_area", "petal_area", "sepal_to_petal_length_ratio"]}

## 8. Image Size and Build Efficiency

| Image | Disk usage | Content size |
| --- | --- | --- |
| Multi-stage (iris-classifier:v1) | 680MB | 155MB |
| Single-stage (naive comparison build) | 698MB | 160MB |

The multi-stage image is about 18MB (roughly 2.6%) smaller. The saving is modest because almost all of the image size comes from scikit-learn, pandas and NumPy, which both versions require. In docker history, the layer holding the installed packages is 383MB, while the trained models are 180kB and serve.py is 16.4kB. Multi-stage builds save much more when a project has heavy build-only dependencies such as compilers.

Layer caching: the first build took 208.1 seconds. Rebuilding with no changes took 3.4 seconds, with every step reported as CACHED.

## 9. Notes

- The container logs show an sklearn UserWarning that X does not have valid feature names. The model was trained on a DataFrame while the server passes a NumPy array. Predictions are not affected.
- The server startup message in the logs is: Iris server listening on port 8000.
- The Docker health check calls /health every 30 seconds, so these requests appear regularly in docker logs.

## 10. Conclusion

The Iris ML application was successfully containerized using a multi-stage Docker build. The model was trained during the image build, the HTTP server returned a valid prediction, and invalid input was handled with an appropriate client error. The health endpoint responded successfully and the container reported a healthy status.

## 11. Cleanup

Stop and remove the running container when finished:

docker stop iris-classifier-container

docker rm iris-classifier-container

The Docker image can be retained locally for future use.
