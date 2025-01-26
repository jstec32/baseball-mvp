def create_colored_table(pdf, data, column_labels, title, color_dict, x_start, y_start, table_width):

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_xy(x_start, y_start)
    pdf.cell(table_width, 10, text=title, align='C', ln=True)

    # Column Width
    column_width = table_width / len(column_labels)

    # Header Row
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(200, 200, 200)  # Light gray background for headers
    for label in column_labels:
        pdf.cell(column_width, 10, label, border=1, align='C', fill=True)
    pdf.ln(10)

    # Table Rows
    pdf.set_font("Helvetica", size=10)
    for row in data:
        for i, cell in enumerate(row):
            # Apply color coding for the pitch type column
            if i == 0 and cell in color_dict:  # Assuming first column is pitch type
                r, g, b = hex_to_rgb(color_dict[cell])
                pdf.set_fill_color(r, g, b)
                pdf.cell(column_width, 10, cell, border=1, align='C', fill=True)
            else:
                pdf.cell(column_width, 10, str(cell), border=1, align='C', fill=False)
        pdf.ln(10)

def hex_to_rgb(hex_color):
    """Convert a hex color string to an RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))