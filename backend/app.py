from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_file, render_template
from scripts.Scouting_Report_Template_Configuration.processing.Generate_PDF import run_pdf_generation
import os
import psycopg2
import psycopg2.extras
app = Flask(__name__)

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


# API to generate scouting report
@app.route('/generate_scouting_report', methods=['POST'])
@app.route('/generate_scouting_report', methods=['POST'])
def generate_scouting_report():
    try:
        # Log incoming POST data for debugging
        data = request.json
        print(f"Received POST data: {data}")

        # Validate that hitter_id and pitcher_id exist in the request
        if 'hitter_id' not in data or 'pitcher_id' not in data:
            raise ValueError("Missing hitter_id or pitcher_id in POST request.")

        hitter_id = str(data['hitter_id'])
        pitcher_id = str(data['pitcher_id'])

        # Log the fetched hitter_id and pitcher_id
        print(f"Received hitter_id: {hitter_id}, pitcher_id: {pitcher_id}")

        # Run the PDF generation
        s3_url = run_pdf_generation(hitter_id, pitcher_id)

        # Return the download link
        if s3_url:
            return jsonify({"pdf_path": s3_url}), 200
        else:
            return jsonify({"error": "Failed to generate scouting report."}), 500

    except Exception as e:
        print(f"Error generating scouting report: {e}")
        return jsonify({"error": str(e)}), 400


# API to download the scouting report
@app.route('/download_scouting_report', methods=['GET'])
def download_scouting_report():
    pdf_path = request.args.get('pdf_path')
    if pdf_path and os.path.exists(pdf_path):
        # Serve the file correctly as a PDF download
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=os.path.basename(pdf_path),  # Set a meaningful download name
            mimetype='application/pdf'  # Ensure correct MIME type
        )
    else:
        return jsonify({"error": "PDF not found"}), 404

@app.route('/dashboard', methods=['GET'])
def dashboard():
    try:
        # Connect to the database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Query for all saved reports
        query = """
        SELECT report_id,hitter_name, pitcher_name, pdf_path, created_at
        FROM scouting_reports
        ORDER BY created_at DESC;
        """
        cursor.execute(query)
        reports = cursor.fetchall()

        # Format the response as JSON
        report_list = [
            {
                "report_id": row[0],
                "hitter_name": row[1],
                "pitcher_name": row[2],
                "pdf_path": row[3],
                "created_at": row[4].strftime("%Y-%m-%d %H:%M:%S")
            } for row in reports
        ]

        cursor.close()
        conn.close()
        return jsonify(report_list)

    except Exception as e:
        print(f"Error fetching reports: {e}")
        return jsonify({"error": "Failed to fetch reports"}), 500

@app.route('/dashboard', methods=['GET'])
def get_reports():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Query previously generated reports
        query = """
        SELECT hitter_name, pitcher_name, created_at, pdf_path
        FROM scouting_reports
        ORDER BY created_at DESC;
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        # Format the result as JSON
        reports = [
            {"hitter_name": row[0], "pitcher_name": row[1], "created_at": row[2], "pdf_path": row[3]}
            for row in rows
        ]
        return jsonify(reports)

    except Exception as e:
        print(f"Error fetching scouting reports: {e}")
        return jsonify({"error": "Failed to fetch reports"}), 500

@app.route('/user_dashboard')
def user_dashboard():
    return render_template('dashboard.html')


@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    feedback_text = request.form.get('feedback')
    feedback_type = request.form.get('feedback_type')
    rating = int(request.form.get('rating'))
    report_id = int(request.form.get('report_id'))
    user_id = int(request.form.get('user_id'))

    connection = None  # Ensure it's initialized before the try block
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=os.getenv("DB_PORT")
        )
        cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Insert feedback into the table
        insert_query = """
        INSERT INTO feedback (report_id, user_id, feedback_text,feedback_type, rating)
        VALUES (%s, %s, %s, %s, %s);
        """
        cursor.execute(insert_query, (report_id, user_id, feedback_text,feedback_type, rating))
        connection.commit()

        return jsonify({"message": "Feedback submitted successfully!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if connection is not None:  # Safeguard against uninitialized variable
            connection.close()


@app.route('/get_feedback/<int:report_id>', methods=['GET'])
def get_feedback(report_id):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Query feedback for the selected report
        query = """
        SELECT feedback_text, rating, timestamp 
        FROM feedback 
        WHERE report_id = %s
        ORDER BY timestamp DESC;
        """
        cursor.execute(query, (report_id,))
        feedback = cursor.fetchall()

        feedback_list = [
            {
                "feedback_text": row[0],
                "rating": row[1],
                "timestamp": row[2].strftime("%Y-%m-%d %H:%M:%S")
            } for row in feedback
        ]

        cursor.close()
        conn.close()
        return jsonify(feedback_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(port=5000, debug=True)
