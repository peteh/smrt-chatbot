from flask import Flask, render_template, send_from_directory, request, send_file, abort, jsonify
import sqlite3
import os
import io
import zipfile
from smrt.db.database import GalleryDatabase
import json
import base64
from smrt.utils import utils

class GalleryFlaskApp:
    def __init__(self, gallery_db: GalleryDatabase):
        self._app = Flask(__name__)
        self._register_routes()
        self._gallery_db = gallery_db

    def _mime_type_to_extension(self, mime_type: str) -> str:
        mapping = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/gif": "gif",
            "image/bmp": "bmp",
            "image/webp": "webp"
        }
        return mapping.get(mime_type, "bin")

    def _register_routes(self):
        @self._app.route("/")
        def home():
            return jsonify({"message": "Hello, World!"})

        @self._app.route("/hello/<name>")
        def hello(name):
            return jsonify({"message": f"Hello, {name}!"})
        
        @self._app.route("/api/v1/images/<gallery_id>")
        def get_images(gallery_id):
            gallery_id_decoded = base64.b64decode(gallery_id).decode('utf-8')
            images = self._gallery_db.get_images(gallery_id_decoded)
            if not images:
                abort(404, "No images found")
            image_list = []
            count = 1
            for image in images:
                extension = self._mime_type_to_extension(image["mime_type"])
                padded_count = str(count).zfill(4)
                image_entry = {
                    "sender": image["sender"],
                    "image_uuid": image["image_uuid"],
                    "time": image["time"],
                    "mime_type": image["mime_type"],
                    "image_name": f"IMAGE_{padded_count}.{extension}",
                    # Assuming a URL structure for accessing individual images
                    #"url": f"/{gallery_id}/images/{filename}"
                }
                image_list.append(image_entry)
            return jsonify(image_list)
        
        @self._app.route("/api/v1/thumb/<gallery_id>/<image_uuid>.png")
        def get_thumbnail(gallery_id, image_uuid):
            gallery_id_decoded = base64.b64decode(gallery_id).decode('utf-8')
            image_data = self._gallery_db.get_image(gallery_id_decoded, image_uuid)
            if not image_data:
                abort(404, "Thumbnail not found")
            image_uuid = image_data["image_uuid"]
            #image_filename = utils.storage_path() + f"/gallery/{image_uuid}.blob"
            thumb_filename = self._gallery_db.get_storage_path() + f"/{image_uuid}_thumb.png"
            return send_file(thumb_filename,
                mimetype='image/png',
                as_attachment=False,
                download_name=f"{image_uuid}_thumb.png"
            )
        
        @self._app.route("/api/v1/image/<gallery_id>/<image_uuid>/<file_name>")
        def get_image(gallery_id, image_uuid, file_name):
            gallery_id_decoded = base64.b64decode(gallery_id).decode('utf-8')
            image_data = self._gallery_db.get_image(gallery_id_decoded, image_uuid)
            if not image_data:
                abort(404, "Thumbnail not found")
            image_uuid = image_data["image_uuid"]
            mime_type = image_data["mime_type"]
            #image_filename = utils.storage_path() + f"/gallery/{image_uuid}.blob"
            local_file_name = self._gallery_db.get_storage_path() + f"/{image_uuid}.blob"
            return send_file(local_file_name,
                mimetype=mime_type,
                as_attachment=False,
                download_name=f"{file_name}"
            )
        
        @self._app.route("/<gallery_id>/download")
        def download_images(gallery_id):
            start = request.args.get("start")
            end = request.args.get("end")
            images = self._gallery_db.get_images(gallery_id)

            if not images:
                abort(404, "No images found")

            memory_file = io.BytesIO()
            with zipfile.ZipFile(memory_file, 'w') as zf:
                for filename, sender, timestamp in images:
                    # todo do path stuff
                    filepath = os.path.join("IMAGE_DIR", filename)
                    if os.path.exists(filepath):
                        zf.write(filepath, arcname=filename)
            memory_file.seek(0)

            # Optional: date range in filename
            zip_name = "gallery.zip"
            if start and end:
                zip_name = f"gallery_{start}_to_{end}.zip"

            return send_file(memory_file, as_attachment=True, download_name=zip_name)

    def run(self, **kwargs):
        self._app.run(**kwargs)
