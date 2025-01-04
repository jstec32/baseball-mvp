# baseball-mvp
Baseball MVP AI Scouting Project

# Baseball MVP Project

## Overview
This project automates the ingestion and storage of baseball data for analysis and prediction. The ultimate goal is to leverage chatgpt to automatically generate scouting reports that take historical data plus the users comments to better create data.

## Setup Instructions
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/baseball-mvp.git
   cd baseball-mvp

Set up a virtual environment:

bash
Copy code
python3 -m venv venv
source venv/bin/activate
Install dependencies:

bash
Copy code
pip install -r requirements.txt
Verify AWS connectivity:

Test S3 upload with scripts/test_s3.py.
Test RDS connection with scripts/test_rds_connection.py.
Run the data ingestion script:

bash
Copy code
python3 scripts/data_ingestion.py
Directory Structure
scripts/: Python scripts for data ingestion and testing.
sql/: SQL files for database schema and queries.
docs/: Documentation files.
AWS Resources
S3 Bucket: Stores ingested baseball data.
RDS Database: Stores structured data for analysis.
