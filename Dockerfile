FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
# RUN apt-get update && \
#     apt-get install -y --no-install-recommends \
#     build-essential \
#     pkg-config \
#     default-libmysqlclient-dev \
#     && rm -rf /var/lib/apt/lists/*

# Copy the requirements file
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir --upgrade pip setuptools wheel -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install --no-cache-dir numpy -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# Copy the entire 'app' directory into the container
COPY ./app /app/app

# The command to run the application
# Uvicorn will run on 0.0.0.0:8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
