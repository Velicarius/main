FROM python:3.11-slim

# чтобы uv был в PATH
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

# ставим uv через pipx
RUN pip install --no-cache-dir pipx && pipx install uv

# зависимости проекта (в системное окружение образа)
COPY backend/requirements.txt /app/requirements.txt
RUN uv pip install --system -r /app/requirements.txt

# код приложения
COPY backend /app/backend

# Ensure Python can import "app" by pointing PYTHONPATH at /app/backend
ENV PYTHONPATH="/app/backend:${PYTHONPATH}"

ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
