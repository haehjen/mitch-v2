from pathlib import Path
from modules import memory

def import_backstory(file_path="data/backstory.txt", tags=None):
    tags = tags or ["backstory"]
    path = Path(file_path)

    if not path.exists():
        print(f"[Backstory Importer] File not found: {file_path}")
        return

    with open(path, "r") as f:
        paragraphs = f.read().split("\n\n")

    count = 0
    for para in paragraphs:
        clean = para.strip().replace("\n", " ")
        if len(clean) > 20:  # avoid tiny fragments
            memory.save_knowledge(clean, tags)
            print(f"[Backstory Importer] Saved: {clean[:80]}...")
            count += 1

    print(f"[Backstory Importer] Imported {count} memory entries.")

if __name__ == "__main__":
    import_backstory()
