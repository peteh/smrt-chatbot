from smrt.db import GalleryDatabase
from smrt.web.galleryweb import GalleryFlaskApp

if __name__ == "__main__":
    gallery_db = GalleryDatabase()  # Ensure database is initialized
    app = GalleryFlaskApp(gallery_db)
    app.run(debug=True)