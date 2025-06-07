from pathlib import Path
from modules import memory
from core.peterjones import get_logger

logger = get_logger("backstory_importer")

def import_backstory(file_path="data/backstory.txt", tags=None):
    tags = tags or ["backstory"]
    path = Path(file_path)

    if not path.exists():
        logger.error(f"File not found: {file_path}")
        return

    with open(path, "r") as f:
        paragraphs = f.read().split("\n\n")

    count = 0
    for para in paragraphs:
        clean = para.strip().replace("\n", " ")
        if len(clean) > 20:  # avoid tiny fragments
            memory.save_knowledge(clean, tags)
            logger.info(f"Saved: {clean[:80]}...")
            count += 1

    logger.info(f"Imported {count} memory entries.")

if __name__ == "__main__":
    import_backstory()
