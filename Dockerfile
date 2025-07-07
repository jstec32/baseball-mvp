FROM python:3.10

WORKDIR /app

# System deps needed for rembg/pymatting/numba
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libopenblas-dev \
    liblapack-dev \
    gfortran \
    ffmpeg

COPY . .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD ["uvicorn", "Query_Generator.wrapper.main_APIs:app", "--host", "0.0.0.0", "--port", "10000"]

