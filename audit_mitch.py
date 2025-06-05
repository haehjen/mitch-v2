import os
import ast
import json

PROJECT_ROOT = "/home/triad/mitch"
SUMMARY_FILE = "mitch_audit_report.txt"
EVENTS_JSON = "mitch_event_map.json"

event_calls = {}
file_structure = {}

def analyze_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except Exception as e:
        return {"error": str(e)}

    info = {
        "imports": [],
        "events_emitted": [],
        "functions": [],
        "classes": []
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
            info["imports"].append(ast.get_source_segment(source, node))
        elif isinstance(node, ast.FunctionDef):
            info["functions"].append(node.name)
        elif isinstance(node, ast.ClassDef):
            info["classes"].append(node.name)
        elif isinstance(node, ast.Call):
            if hasattr(node.func, 'attr') and node.func.attr == "emit":
                if node.args and isinstance(node.args[0], ast.Constant):
                    event_name = getattr(node.args[0], "value", None)
                    if isinstance(event_name, str):
                        info["events_emitted"].append(event_name)
                        event_calls.setdefault(event_name, []).append(filepath)

    return info

def scan_project(root):
    for dirpath, dirnames, filenames in os.walk(root):
        # Exclude common non-source directories
        dirnames[:] = [
            d for d in dirnames
            if not d.startswith("venv")
            and not d.startswith(".")
            and d != "__pycache__"
        ]
        for fname in filenames:
            if fname.endswith(".py"):
                full_path = os.path.join(dirpath, fname)
                rel_path = os.path.relpath(full_path, root)
                file_structure[rel_path] = analyze_file(full_path)

def write_summary():
    with open(SUMMARY_FILE, "w") as out:
        out.write("=== MITCH AUDIT REPORT ===\n\n")
        for f, data in file_structure.items():
            out.write(f"[{f}]\n")
            if "error" in data:
                out.write(f"  ERROR: {data['error']}\n\n")
                continue
            out.write(f"  Classes: {', '.join(data['classes'])}\n")
            out.write(f"  Functions: {', '.join(data['functions'])}\n")
            out.write(f"  Events Emitted: {', '.join(data['events_emitted'])}\n\n")

    with open(EVENTS_JSON, "w") as out_json:
        json.dump(event_calls, out_json, indent=2)

if __name__ == "__main__":
    scan_project(PROJECT_ROOT)
    write_summary()
    print("? MITCH audit complete. Files:")
    print(f"- {SUMMARY_FILE}")
    print(f"- {EVENTS_JSON}")
