import os, glob, re
target = 'frontend/template/*.html'
files = glob.glob(target)
files.append('frontend/index.html')
for f in files:
    if not os.path.exists(f): continue
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    new_content = re.sub(r'app\.js(\?v=[0-9.]+)?', 'app.js?v=2.7', content)
    if new_content != content:
        with open(f, 'w', encoding='utf-8') as file:
            file.write(new_content)
        print(f'Updated {f}')
