import sys

def lint_brackets(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return

    # A simple but more robust bracket matching that ignores strings and single-line comments.
    stack = []
    in_string = False
    string_char = None
    in_comment = False
    in_regex = False
    
    i = 0
    while i < len(text):
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
            
        if char == '/' and i + 1 < len(text) and text[i+1] == '/':
            in_comment = True
            i += 2
            continue

        if char in '{[(':
            stack.append((char, i))
        elif char in '}])':
            if not stack:
                print(f"Mismatched extra '{char}' at index {i} (line {text[:i].count('\\n') + 1})")
                
                # Print context
                start = max(0, i - 50)
                end = min(len(text), i + 50)
                print("Context:", repr(text[start:end]))
                
                return
            else:
                top, pos = stack.pop()
                expected = {'{': '}', '[': ']', '(': ')'}[top]
                if char != expected:
                    print(f"Mismatched closing '{char}' at index {i} (line {text[:i].count('\\n') + 1}). Expected '{expected}' to match '{top}' at index {pos} (line {text[:pos].count('\\n') + 1}).")
                    return
        i += 1
        
    if stack:
        for char, pos in stack:
            print(f"Unclosed '{char}' at index {pos} (line {text[:pos].count('\\n') + 1})")

if __name__ == '__main__':
    lint_brackets('frontend/js/app.js')
