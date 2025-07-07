FROM python:3.10-slim

WORKDIR /app

# Install OS dependencies
RUN apt-get update && apt-get install -y build-essential libgl1-mesa-glx

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Run the FastAPI app
CMD ["uvicorn", "Query_Generator.wrapper.main_APIs:app", "--host", "0.0.0.0", "--port", "10000"]
