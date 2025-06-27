# Use a lightweight Python base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy app files
COPY . /app

# Give ffmpeg executable permission (if not already done)
RUN chmod +x ./ffmpeg

# Install Python dependencies
COPY requirements.txt ./requirements.txt
RUN pip3 install -r requirements.txt

# Expose Flask's default port
EXPOSE 5000

# Set environment variables (optional)
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_ENV=development

# Run the app
CMD ["flask", "run"]

