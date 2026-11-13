FROM python:3.11-slim

WORKDIR /code

# Copy requirements first to leverage Docker layer caching
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the app payload
COPY ./app /code/app

# Expose port 80 for the ALB/ECS mapping
EXPOSE 80

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]