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
    
    def _get_file_name(self, count: int, mime_type: str) -> str:
        extension = self._mime_type_to_extension(mime_type)
        padded_count = str(count).zfill(4)
        return f"IMAGE_{padded_count}.{extension}"

    def _register_routes(self):
        @self._app.route("/")
        def home():
            return jsonify({"message": "Hello, World!"})

        @self._app.route("/gallery/<gallery_id>")
        def show_gallery(gallery_id):
            return render_template("gallery.html", gallery_uuid=gallery_id)
        
        @self._app.route("/api/v1/images/<gallery_id>")
        def get_images(gallery_id):
            chat_id = self._gallery_db.get_chat_id_from_gallery_uuid(gallery_id)
            if chat_id is None:
                abort(404, "No images found")
            images = self._gallery_db.get_images(chat_id)
            if not images:
                abort(404, "No images found")
            image_list = []
            count = 1
            for image in images:
                image_entry = {
                    "sender": image["sender"],
                    "image_uuid": image["image_uuid"],
                    "time": image["time"],
                    "mime_type": image["mime_type"],
                    "image_name": self._get_file_name(count, image["mime_type"]),
                }
                image_list.append(image_entry)
                count += 1
            return jsonify(image_list)
        
        @self._app.route("/api/v1/thumb/<gallery_id>/<image_uuid>.png")
        def get_thumbnail(gallery_id, image_uuid):
            chat_id = self._gallery_db.get_chat_id_from_gallery_uuid(gallery_id)
            image_data = self._gallery_db.get_image(chat_id, image_uuid)
            if not image_data:
                abort(404, "Thumbnail not found")
            image_uuid = image_data["image_uuid"]
            #image_filename = utils.storage_path() + f"/gallery/{image_uuid}.blob"
            thumb_filename = self._gallery_db.get_storage_path() / f"{image_uuid}_thumb.png"
            return send_file(thumb_filename,
                mimetype='image/png',
                as_attachment=False,
                download_name=f"{image_uuid}_thumb.png"
            )
        
        @self._app.route("/api/v1/image/<string:gallery_id>/<string:image_uuid>/<string:file_name>")
        def get_image(gallery_id, image_uuid, file_name):
            chat_id = self._gallery_db.get_chat_id_from_gallery_uuid(gallery_id)
            image_data = self._gallery_db.get_image(chat_id, image_uuid)
            if not image_data:
                abort(404, "Thumbnail not found")
            image_uuid = image_data["image_uuid"]
            mime_type = image_data["mime_type"]
            #image_filename = utils.storage_path() + f"/gallery/{image_uuid}.blob"
            local_file_name = self._gallery_db.get_storage_path() / f"{image_uuid}.blob"
            return send_file(local_file_name,
                mimetype=mime_type,
                as_attachment=False,
                download_name=f"{file_name}"
            )
        
        @self._app.route("/api/v1/download/<string:gallery_id>/<string:gallery_file_name>")
        def download_images(gallery_id, gallery_file_name):
            start = request.args.get("start")
            end = request.args.get("end")
            chat_id = self._gallery_db.get_chat_id_from_gallery_uuid(gallery_id)
            if chat_id is None:
                abort(404, "No images found")
            images = self._gallery_db.get_images(chat_id)

            if not images:
                abort(404, "No images found")

            memory_file = io.BytesIO()
            with zipfile.ZipFile(memory_file, 'w') as zf:
                count = 1
                for image in images:
                    image_uuid = image["image_uuid"]
                    file_name = self._get_file_name(count, image["mime_type"])
                    # todo do path stuff
                    filepath = self._gallery_db.get_storage_path() / f"{image_uuid}.blob"
                    if os.path.exists(filepath):
                        zf.write(filepath, arcname=file_name)
                    count += 1
            memory_file.seek(0)

            # Optional: date range in filename
            zip_name = "gallery.zip"
            if start and end:
                zip_name = f"gallery_{start}_to_{end}.zip"

            return send_file(memory_file, as_attachment=True, download_name=zip_name)

    def run(self, **kwargs):
        self._app.run(**kwargs)
