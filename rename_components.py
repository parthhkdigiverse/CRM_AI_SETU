import os
import glob
import re

template_dir = r"e:\CRM AI SETU\frontend\template"
html_files = glob.glob(os.path.join(template_dir, "*.html"))

for file_path in html_files:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Failed to read {file_path}: {e}")
        continue

    # Replace components.js occurrences with ui_components.js
    new_content = re.sub(r'components\.js(\?v=[\d\.]+)?', 'ui_components.js', content)

    # Write back only if changed
    if content != new_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Updated {file_path}")
