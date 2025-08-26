#!/usr/bin/env python3
"""
Script to fix indentation issues in main.py
"""

import re

def fix_indentation():
    """Fix indentation issues in main.py"""
    
    # Read the file
    with open('main.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Fix specific problematic areas
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Fix: if text_processor: after else: (around line 1492)
        if (i > 1490 and i < 1495 and 
            'else:' in line and 
            i + 1 < len(lines) and 
            '# Fallback to original text processor' in lines[i + 1] and
            i + 2 < len(lines) and 
            'if text_processor:' in lines[i + 2]):
            
            # Add proper indentation to if text_processor:
            fixed_lines.append(line)  # else:
            fixed_lines.append(lines[i + 1])  # comment
            fixed_lines.append('                ' + lines[i + 2].lstrip())  # if text_processor: with proper indent
            i += 3
            continue
        
        # Fix: except Exception as text_error: (around line 1522)
        if (i > 1520 and i < 1525 and 
            'except Exception as text_error:' in line):
            
            # Fix the except line
            fixed_lines.append('                    ' + line.lstrip())
            i += 1
            continue
        
        # Fix: logger.error after except (around line 1523)
        if (i > 1522 and i < 1527 and 
            'logger.error(f"Text processing error:' in line):
            
            # Fix the logger.error line
            fixed_lines.append('                        ' + line.lstrip())
            i += 1
            continue
        
        # Fix: await processing_msg.edit_text after fallback_text (around line 1540)
        if (i > 1538 and i < 1543 and 
            'await processing_msg.edit_text(' in line):
            
            # Fix the await line
            fixed_lines.append('                        ' + line.lstrip())
            i += 1
            continue
        
        # Default: keep the line as is
        fixed_lines.append(line)
        i += 1
    
    # Write the fixed file
    with open('main.py', 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    print("✅ Indentation fixes applied to main.py")

if __name__ == "__main__":
    fix_indentation() 