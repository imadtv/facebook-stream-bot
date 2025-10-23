FROM python:3.11-slim

# تثبيت FFmpeg ومتطلبات SSL
RUN apt update && apt install -y ffmpeg ca-certificates libssl-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# تثبيت مكتبات البايثون
RUN pip install --no-cache-dir -r requirements.txt

# لا نضع التوكن داخل Dockerfile
# التوكن سيتم تمريره عند تشغيل الحاوية

CMD ["python", "main.py"]
