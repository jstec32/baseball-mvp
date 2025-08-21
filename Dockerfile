FROM ubuntu:22.04

# Install Python & dependencies
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y python3.10 python3.10-dev python3.10-venv python3-pip && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libopenblas-dev \
    liblapack-dev \
    gfortran \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev && \
    rm -rf /var/lib/apt/lists/*

# Create app folder and copy files
WORKDIR /app
COPY . .

# Install Python deps
RUN python3.10 -m pip install --upgrade pip
RUN python3.10 -m pip install -r requirements.txt
RUN python3.10 -m pip install --use-deprecated=legacy-resolver -r requirements.txt

# Run app
CMD ["python3.10", "-m", "uvicorn", "Query_Generator.wrapper.main_APIs:app", "--host", "0.0.0.0", "--port", "10000"]
