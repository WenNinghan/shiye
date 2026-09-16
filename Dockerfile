FROM node:24-bookworm-slim AS web
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-fund --no-audit
COPY web/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 fonts-noto-cjk && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements-lock.txt /app/backend/requirements-lock.txt
RUN pip install --no-cache-dir -r backend/requirements-lock.txt
COPY backend/ /app/backend/
COPY scripts/make_samples.py /app/scripts/make_samples.py
COPY --from=web /build/web/dist /app/web/dist
RUN python scripts/make_samples.py --output /app/web/dist/examples && useradd --uid 10001 --create-home shiye && mkdir /data && chown shiye:shiye /data
ENV SHIYE_DATA_DIR=/data
USER shiye
WORKDIR /app/backend
EXPOSE 8765
CMD ["python", "-m", "uvicorn", "shiye.main:app", "--host", "0.0.0.0", "--port", "8765", "--workers", "1"]
