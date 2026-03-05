import sys

text = open('frontend/js/app.js', encoding='utf-8').read()
idx = 139950
start = max(0, idx - 100)
end = min(len(text), idx + 100)
snippet = text[start:end]
print("--- Context around Error ---")
print(snippet)

lines = text[:idx].split('\n')
print(f"--- Line number: {len(lines)} ---")

# Let's also do a fresh bracket count just to be safe
stack = []
for i, char in enumerate(text):
    if char in '{[(': stack.append((char, i, len(text[:i].split('\n'))))
    elif char in '}])':
        if not stack:
            print(f"Mismatched {char} at line {len(text[:i].split('\n'))}")
            break
        top, pos, line = stack.pop()
        if (char == '}' and top != '{') or (char == ']' and top != '[') or (char == ')' and top != '('):
            print(f"Mismatched closing {char} at line {len(text[:i].split('\n'))}, matches {top} at line {line}")
            break
