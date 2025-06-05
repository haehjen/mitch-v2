import os
import ast
import json

PROJECT_ROOT = "/home/triad/mitch"
MEMORY_AUDIT_FILE = "mitch_memory_audit.txt"

memory_keywords = {
    "memory": ["save", "recall", "clear", "truncate", "load"],
    "emotion": ["emotion", "mood"],
    "knowledge": ["knowledge"],
    "persona": ["persona"]
}

results = {}

def analyze_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except Exception as e:
        return {"error": str(e)}

    info = {
        "functions": [],
        "matches": []
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            info["functions"].append(node.name)

        if isinstance(node, ast.Name):
            for category, keywords in memory_keywords.items():
                if any(kw in node.id.lower() for kw in keywords):
                    info["matches"].append((category, node.id))

    return info

def scan_memory_related_files(root):
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            if fname.endswith(".py") and any(memfile in fname.lower() for memfile in ["memory", "emotion", "persona", "knowledge"]):
                full_path = os.path.join(dirpath, fname)
                rel_path = os.path.relpath(full_path, root)
                results[rel_path] = analyze_file(full_path)

scan_memory_related_files(PROJECT_ROOT)

with open(MEMORY_AUDIT_FILE, "w") as out:
    for f, data in results.items():
        out.write(f"[{f}]\n")
        if "error" in data:
            out.write(f"  ERROR: {data['error']}\n\n")
            continue
        out.write(f"  Functions: {', '.join(data['functions'])}\n")
        out.write("  Keyword Matches:\n")
        for category, name in data["matches"]:
            out.write(f"    - [{category}] {name}\n")
        out.write("\n")

MEMORY_AUDIT_FILE
