FROM python:3.12-alpine

WORKDIR /usr/src/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

ENV PORT=3000
ENV IMAGE_DIR=/usr/src/app/images

CMD ["python", "-u", "main.py"]
