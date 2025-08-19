FROM python:3.10

WORKDIR /app

# Add extra dependencies for compiling packages
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    build-essential \
    python3.10-dev \
    python3-dev \
    libpq-dev \
    cmake \
    g++ \
    gcc \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libopenblas-dev \
    liblapack-dev \
    gfortran \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# Pre-install pip build tools
RUN pip install --upgrade pip setuptools wheel

# Install Python dependencies
RUN pip install -r requirements.txt

CMD ["uvicorn", "Query_Generator.wrapper.main_APIs:app", "--host", "0.0.0.0", "--port", "10000"]
