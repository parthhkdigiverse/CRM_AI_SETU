import os
import glob

template_dir = r"e:\CRM AI SETU\frontend\template"
html_files = glob.glob(os.path.join(template_dir, "*.html"))

for file_path in html_files:
    try:
        # Try reading as utf-16 (from PowerShell)
        with open(file_path, "r", encoding="utf-16") as f:
            content = f.read()
    except UnicodeError:
        try:
            # Fallback to utf-8 if it's already utf-8
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeError:
            print(f"Failed to read {file_path}")
            continue

    # Add components cache bust string if missing
    import re
    content = re.sub(r'components\.js(\?v=[\d\.]+)?', 'components.js?v=2.5', content)
    content = re.sub(r'auth\.js(\?v=[\d\.]+)?', 'auth.js?v=2.3', content)
    content = re.sub(r'app\.js(\?v=[\d\.]+)?', 'app.js?v=2.4', content)

    # Write back as utf-8
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Fixed {file_path}")
