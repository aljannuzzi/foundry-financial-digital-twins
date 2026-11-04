FROM node:22-bookworm-slim AS ui-build
ARG NPM_REGISTRY=https://registry.npmjs.org/
WORKDIR /app/ui
RUN npm config set registry "${NPM_REGISTRY}" \
    && npm install --global pnpm@12.16.1
COPY ui/package.json ui/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY ui/ ./
RUN pnpm build

FROM python:3.13-slim AS runtime
ARG PIP_INDEX_URL=https://pypi.org/simple
ENV PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000
WORKDIR /app
COPY pyproject.toml README.md requirements-runtime.txt ./
COPY src/ ./src/
COPY --from=ui-build /app/ui/dist ./ui/dist
RUN pip install --no-cache-dir setuptools wheel \
    && pip install --no-cache-dir -r requirements-runtime.txt \
    && pip install --no-cache-dir --no-build-isolation --no-deps .
EXPOSE 8000
CMD ["sh", "-c", "uvicorn financial_twins.api:app --host 0.0.0.0 --port ${PORT}"]
