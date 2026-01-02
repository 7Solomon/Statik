# Build React frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Setup Python backend
FROM python:3.11-slim AS backend
WORKDIR /app
ENV RUNNING_IN_DOCKER=true

# Copy backend requirements and install dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code and conf
COPY backend/src ./src
COPY backend/wsgi.py ./
COPY backend/gunicorn.conf.py ./


# Copy built frontend from previous stage
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Create content directory with proper permissions
RUN mkdir -p content/system_templates && \
    chmod -R 777 content

# Expose port
EXPOSE 8000

# Run Flask app with gunicorn for production
CMD ["gunicorn", "-c", "gunicorn.conf.py", "wsgi:app"]
