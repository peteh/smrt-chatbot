from smrt.db import GalleryDatabase
from smrt.bot.pipeline.pipeline_sniper import KleinanzeigenScheduledTask

if __name__ == "__main__":
    kleinzeigen = KleinanzeigenScheduledTask("39c3", None, None)
    results = kleinzeigen.run()

