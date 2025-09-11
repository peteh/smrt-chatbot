from flask import Flask, render_template, send_from_directory, request, send_file, abort
import sqlite3
import os
import io
import zipfile

app = Flask(__name__)

DB_PATH = "gallery.db"
IMAGE_DIR = "images"

def get_images(group_id, start=None, end=None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if start and end:
        cur.execute("""
            SELECT filename, sender, timestamp FROM images
            WHERE group_id = ? AND date(timestamp) BETWEEN date(?) AND date(?)
            ORDER BY id DESC
        """, (group_id, start, end))
    else:
        cur.execute("""
            SELECT filename, sender, timestamp FROM images
            WHERE group_id = ?
            ORDER BY id DESC
        """, (group_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

@app.route("/<group_id>/")
def gallery(group_id):
    start = request.args.get("start")
    end = request.args.get("end")

    images = get_images(group_id, start, end)

    # Min/max dates for slider
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT MIN(date(timestamp)), MAX(date(timestamp)) FROM images WHERE group_id = ?", (group_id,))
    min_date, max_date = cur.fetchone()
    conn.close()

    if not min_date:  # no images for this group
        return f"<h1>No images for group {group_id}</h1>"

    return render_template("gallery.html",
                           images=images,
                           group_id=group_id,
                           start=start,
                           end=end,
                           min_date=min_date,
                           max_date=max_date)

@app.route("/<group_id>/images/<path:filename>")
def serve_image(group_id, filename):
    return send_from_directory(IMAGE_DIR, filename)

@app.route("/<group_id>/download")
def download_images(group_id):
    start = request.args.get("start")
    end = request.args.get("end")
    images = get_images(group_id, start, end)

    if not images:
        abort(404, "No images found")

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for filename, sender, timestamp in images:
            filepath = os.path.join(IMAGE_DIR, filename)
            if os.path.exists(filepath):
                zf.write(filepath, arcname=filename)
    memory_file.seek(0)

    # Optional: date range in filename
    zip_name = "gallery.zip"
    if start and end:
        zip_name = f"gallery_{start}_to_{end}.zip"

    return send_file(memory_file, as_attachment=True, download_name=zip_name)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
