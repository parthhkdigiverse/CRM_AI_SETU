import sys

text = open('frontend/js/app.js', encoding='utf-8').read()

stack = []
in_string = False
string_char = None
in_comment = False

i = 0
while i < len(text) - 6: # just before the last `});\n`
    char = text[i]
    
    if in_comment:
        if char == '\n':
            in_comment = False
        i += 1
        continue
        
    if in_string:
        if char == '\\':
            i += 2
            continue
        if char == string_char:
            in_string = False
        i += 1
        continue
        
    if char in '"\'`':
        in_string = True
        string_char = char
        i += 1
        continue
        
    if char == '/' and text[i+1] == '/':
        in_comment = True
        i += 2
        continue

    line = len(text[:i].split('\n'))
    if char in '{[(':
        stack.append((char, line))
    elif char in '}])':
        if stack:
            # For simplicity, don't check mismatch types here, just assume well-formed until the missing bracket
            stack.pop()
    
    i += 1

print(f"Stack right before the end: {stack}")
if len(stack) > 1:
    print(f"Likely missing a '}}' matching the '{{' at line {stack[-1][1]}")
