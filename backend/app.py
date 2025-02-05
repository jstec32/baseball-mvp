from flask import Flask, request, jsonify, send_file, render_template
from scripts.Scouting_Report_Template_Configuration.processing.Generate_PDF import run_pdf_generation
import os
import psycopg2
app = Flask(__name__)

# Database configuration
DB_CONFIG = {
    "host": "aws-0-us-east-2.pooler.supabase.com",
    "database": "postgres",
    "user": "postgres.chcovbrcpmlxyauansqe",
    "password": "1Z4IO6fxxYw8PgxL",  # Replace with your Supabase password
    "port": 5432  # Default PostgreSQL port
}
# Serve the UI
@app.route('/')
def index():
    # Fetch hitter and pitcher names from the database
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""SELECT CONCAT("First_Name", ' ', "Last_Name") AS player_name FROM players;""")
    player_names = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()

    return render_template('UI_PromptGen.html', players=player_names)


# API to fetch player suggestions dynamically
@app.route('/player_suggestions')
def player_suggestions():
    query = request.args.get('query', '')

    # Query the database for player names matching the input query
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""
            SELECT key_mlbam, CONCAT("First_Name", ' ', "Last_Name") AS player_name 
            FROM players 
            WHERE CONCAT("First_Name", ' ', "Last_Name") ILIKE %s 
            LIMIT 10;
        """, (f'%{query}%',))
    players = [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
    cursor.close()
    conn.close()

    return jsonify(players)


# API to generate scouting report
@app.route('/generate_scouting_report', methods=['POST'])
def generate_scouting_report():
    try:
        # Get hitter and pitcher IDs from the request
        data = request.json
        hitter_id = data['hitter_id']
        pitcher_id = data['pitcher_id']

        # Run the PDF generation
        pdf_path = run_pdf_generation(hitter_id, pitcher_id)

        # Return the path of the generated PDF
        if pdf_path and os.path.exists(pdf_path):
            return jsonify({"pdf_path": pdf_path}), 200
        else:
            return jsonify({"error": "Failed to generate scouting report."}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# API to download the scouting report
@app.route('/download_scouting_report', methods=['GET'])
def download_scouting_report():
    pdf_path = request.args.get('pdf_path')
    if pdf_path and os.path.exists(pdf_path):
        return send_file(pdf_path, as_attachment=True)
    else:
        return jsonify({"error": "PDF not found"}), 404


if __name__ == '__main__':
    app.run(port=5000, debug=True)
