# Stage 1: build the React app into backend/app/static
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN mkdir -p /backend/app && npx vite build --outDir /backend/app/static --emptyOutDir

# Stage 2: FastAPI serving the API, the static bundle and the index.html template
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=web /backend/app/static ./app/static
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
