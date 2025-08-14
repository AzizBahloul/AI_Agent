FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN apt-get update && apt-get install -y libx11-6 xvfb x11-utils && pip install -r requirements.txt
COPY executor.py .
CMD ["python","executor.py"]
