FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY searchlitex ./searchlitex
RUN useradd --system --create-home appuser
USER appuser
EXPOSE 8000
CMD ["uvicorn", "searchlitex.api:app", "--host", "0.0.0.0", "--port", "8000"]
