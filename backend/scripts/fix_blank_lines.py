#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re

def fix_blank_lines(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace blank lines containing whitespace with empty lines
    fixed_content = re.sub(r'^\s+$', '', content, flags=re.MULTILINE)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)

if __name__ == '__main__':
    # Fix search_service.py
    search_service_path = os.path.join('app', 'services', 'search_service.py')
    fix_blank_lines(search_service_path)
    print(f"Fixed blank lines in {search_service_path}")
