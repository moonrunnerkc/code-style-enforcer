# Author: Bradley R. Kinnard — determinism is underrated

"""
Normalize code and hash it. Same logic = same hash regardless of formatting.
"""

import hashlib
import re


def normalize_code(code: str) -> str:
    """
    Strip comments, collapse whitespace, kill blank lines.
    Not trying to be a full parser, just consistent enough for cache keys.
    """
    lines = []
    for line in code.splitlines():
        # nuke inline comments (naive, doesn't handle strings, good enough)
        line = re.sub(r'#.*$', '', line)
        line = re.sub(r'//.*$', '', line)
        # normalize around operators so 'x=1' and 'x = 1' match
        line = re.sub(r'\s*([=+\-*/<>!&|,;:{}()\[\]])\s*', r'\1', line)
        # collapse remaining whitespace
        line = ' '.join(line.split())
        if line:
            lines.append(line)
    return '\n'.join(lines)


def compute_code_hash(code: str) -> str:
    """sha256 of normalized code. deterministic, fast, no surprises."""
    normalized = normalize_code(code)
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
