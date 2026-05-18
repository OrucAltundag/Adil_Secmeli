"""Trim trailing whitespace and ensure single newline at EOF for .py files under app/.
Run from project root.
"""
import os

root = os.path.join(os.path.dirname(__file__), "..")
app_dir = os.path.join(root, "app")

changed = 0
for dirpath, dirnames, filenames in os.walk(app_dir):
    for fn in filenames:
        if not fn.endswith(".py"):
            continue
        path = os.path.join(dirpath, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            continue
        new_lines = [l.rstrip() + "\n" for l in lines]
        # Remove trailing blank lines
        while len(new_lines) > 1 and new_lines[-1].strip() == "":
            new_lines.pop()
        # Ensure exactly one newline at EOF
        if not new_lines:
            new_lines = ["\n"]
        if not new_lines[-1].endswith("\n"):
            new_lines[-1] = new_lines[-1] + "\n"
        if new_lines != lines:
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            changed += 1
print(f"Trimmed {changed} files.")
