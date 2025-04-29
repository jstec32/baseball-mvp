from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_file, render_template
import os
import psycopg2
import psycopg2.extras
from scripts.Hitter_Report_Card.Visualizations.Hitter_Report_PDF import generate_hitter_report_pdf
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Database configuration
import os
load_dotenv()

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": int(os.getenv("DB_PORT", 5432))  # Default port 5432 if not set
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




# API to download the scouting report
@app.route('/download_scouting_report', methods=['GET'])
def download_scouting_report():
    pdf_path = request.args.get('pdf_path')
    if pdf_path and os.path.exists(pdf_path):
        return send_file(
            pdf_path,
            as_attachment=False,  # 🔁 view inline
            download_name=os.path.basename(pdf_path),
            mimetype='application/pdf'
        )
    else:
        return jsonify({"error": "PDF not found"}), 404


@app.route('/generate_hitter_report', methods=['POST'])
def generate_hitter_report():
    try:
        data = request.json
        player_id = data.get('player_id')
        game_date = data.get('game_date')

        if not player_id or not game_date:
            return jsonify({"error": "Missing player_id or game_date"}), 400

        print(f"Generating report for player_id={player_id}, game_date={game_date}")

        s3_url = generate_hitter_report_pdf(player_id=str(player_id), game_date=game_date)

        if s3_url:
            return jsonify({"pdf_url": s3_url}), 200
        else:
            return jsonify({"error": "PDF generation or upload failed"}), 500

    except Exception as e:
        print(f"Error generating report: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(port=5000, debug=True)
