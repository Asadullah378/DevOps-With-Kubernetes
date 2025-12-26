FROM python:3.12-alpine

WORKDIR /usr/src/app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY main.py .

# Run the application
CMD ["python", "-u", "main.py"]

