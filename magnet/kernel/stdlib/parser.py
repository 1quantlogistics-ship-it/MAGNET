"""
Parse MAGNET design programs into AST.

The kernel knows geometry, not design.
Agents propose geometric primitives, the kernel validates physics.
"""

import re
import json
from typing import List, Dict, Any, Optional

from .ast_nodes import (
    Program, Statement, CreateStatement, UpdateStatement,
    DeleteStatement, LoftStatement, MirrorStatement,
    AlignStatement, ConstrainStatement, DeriveStatement, SetStatement,
    AskStatement,
)


class ParseError(Exception):
    """Raised when parsing fails."""
    def __init__(self, message: str, line: int = 0):
        self.line = line
        super().__init__(f"Line {line}: {message}")


def parse(program_text: str) -> Program:
    """
    Parse design program text into AST.
    
    Syntax:
        CREATE type id { json_properties }
        UPDATE id { json_properties }
        DELETE id
        SET path = value
        LOFT id FROM [id1, id2, ...]
        MIRROR id AS new_id
        ALIGN id TO target AXIS axis
        CONSTRAIN path >= value
        DERIVE path FROM policy(inputs)
    
    Comments start with # or //
    """
    statements = []
    lines = program_text.strip().split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        line_num = i + 1
        
        # Skip empty lines and comments
        if not line or line.startswith('#') or line.startswith('//'):
            i += 1
            continue
        
        # Remove inline comments
        comment_idx = line.find('#')
        if comment_idx > 0:
            line = line[:comment_idx].strip()
        comment_idx = line.find('//')
        if comment_idx > 0:
            line = line[:comment_idx].strip()
        
        if not line:
            i += 1
            continue
        
        # Parse statement
        stmt, lines_consumed = _parse_statement(line, line_num, lines, i)
        if stmt:
            statements.append(stmt)
        
        i += lines_consumed
    
    return Program(statements=statements)


def _parse_statement(line: str, line_num: int, lines: List[str], idx: int) -> tuple:
    """Parse a single statement. Returns (statement, lines_consumed)."""
    
    # CREATE geometry.section bow { ... }
    create_match = re.match(
        r'CREATE\s+(\S+)\s+(\w+)\s*(\{.*)?',
        line,
        re.IGNORECASE
    )
    if create_match:
        resource_type = create_match.group(1)
        resource_id = create_match.group(2)
        props_str = create_match.group(3) or '{}'
        
        # Handle multi-line properties
        lines_consumed = 1
        if props_str.strip() == '{' or ('{' in props_str and '}' not in props_str):
            props_str, lines_consumed = _collect_multiline_json(lines, idx)
        elif not props_str.strip().endswith('}'):
            props_str, lines_consumed = _collect_multiline_json(lines, idx)
        
        properties = _parse_properties(props_str, line_num)
        return CreateStatement(
            resource_type=resource_type,
            resource_id=resource_id,
            properties=properties,
            line_number=line_num
        ), lines_consumed

    # UPDATE bow { ... }
    update_match = re.match(r'UPDATE\s+(\w+)\s*(\{.*)?', line, re.IGNORECASE)
    if update_match:
        resource_id = update_match.group(1)
        props_str = update_match.group(2) or '{}'
        lines_consumed = 1
        if not props_str.strip().endswith('}'):
            props_str, lines_consumed = _collect_multiline_json(lines, idx)
        properties = _parse_properties(props_str, line_num)
        return UpdateStatement(
            resource_id=resource_id,
            properties=properties,
            line_number=line_num
        ), lines_consumed

    # DELETE bow
    delete_match = re.match(r'DELETE\s+(\w+)', line, re.IGNORECASE)
    if delete_match:
        return DeleteStatement(
            resource_id=delete_match.group(1),
            line_number=line_num
        ), 1

    # SET hull.beam = 4.5
    set_match = re.match(
        r'SET\s+(\S+)\s*=\s*(.+)',
        line,
        re.IGNORECASE
    )
    if set_match:
        path = set_match.group(1)
        value_str = set_match.group(2).strip()
        value = _parse_value(value_str)
        return SetStatement(
            path=path,
            value=value,
            line_number=line_num
        ), 1

    # LOFT main_surface FROM [bow, mid, stern]
    loft_match = re.match(
        r'LOFT\s+(\w+)\s+FROM\s+\[([^\]]+)\]',
        line,
        re.IGNORECASE
    )
    if loft_match:
        surface_id = loft_match.group(1)
        sections = [s.strip().strip('"\'') for s in loft_match.group(2).split(',')]
        return LoftStatement(
            surface_id=surface_id,
            section_ids=sections,
            line_number=line_num
        ), 1

    # MIRROR port_rail AS stbd_rail
    mirror_match = re.match(
        r'MIRROR\s+(\w+)\s+AS\s+(\w+)',
        line,
        re.IGNORECASE
    )
    if mirror_match:
        return MirrorStatement(
            source_id=mirror_match.group(1),
            target_id=mirror_match.group(2),
            line_number=line_num
        ), 1

    # ALIGN rail TO chine AXIS y
    align_match = re.match(
        r'ALIGN\s+(\w+)\s+TO\s+(\w+)\s+AXIS\s+(\w+)',
        line,
        re.IGNORECASE
    )
    if align_match:
        return AlignStatement(
            resource_id=align_match.group(1),
            target_id=align_match.group(2),
            axis=align_match.group(3).lower(),
            line_number=line_num
        ), 1

    # CONSTRAIN hull.gm >= 0.5
    constrain_match = re.match(
        r'CONSTRAIN\s+(\S+)\s*(>=|<=|==|>|<)\s*(\S+)',
        line,
        re.IGNORECASE
    )
    if constrain_match:
        return ConstrainStatement(
            path=constrain_match.group(1),
            operator=constrain_match.group(2),
            value=float(constrain_match.group(3)),
            line_number=line_num
        ), 1

    # ASK "How many hulls?" { options: ["1","2"] }
    ask_match = re.match(r'ASK\s+\"([^\"]+)\"\s*(\{.*)?', line, re.IGNORECASE)
    if ask_match:
        question = ask_match.group(1)
        props_str = ask_match.group(2) or "{}"
        lines_consumed = 1
        if props_str.strip() == "{" or ("{" in props_str and "}" not in props_str):
            props_str, lines_consumed = _collect_multiline_json(lines, idx)
        elif props_str and not props_str.strip().endswith("}"):
            props_str, lines_consumed = _collect_multiline_json(lines, idx)

        props = _parse_properties(props_str, line_num)
        options = props.get("options") or []
        if not isinstance(options, list):
            options = []
        options = [str(o) for o in options]
        return AskStatement(question=question, options=options, line_number=line_num), lines_consumed

    # DERIVE hull.beam FROM lb_ratio(loa=hull.loa, target_ratio=5.5)
    derive_match = re.match(
        r'DERIVE\s+(\S+)\s+FROM\s+(\w+)\(([^)]*)\)',
        line,
        re.IGNORECASE
    )
    if derive_match:
        target = derive_match.group(1)
        policy = derive_match.group(2)
        inputs_str = derive_match.group(3)
        inputs = _parse_derive_inputs(inputs_str)
        return DeriveStatement(
            target_path=target,
            policy_name=policy,
            inputs=inputs,
            line_number=line_num
        ), 1

    raise ParseError(f"Unrecognized statement: {line}", line_num)


def _parse_value(value_str: str) -> Any:
    """Parse a value string into Python value."""
    value_str = value_str.strip()
    
    # Try JSON first (handles arrays, objects, booleans, null)
    try:
        return json.loads(value_str)
    except (json.JSONDecodeError, ValueError):
        pass
    
    # Try float
    try:
        return float(value_str)
    except ValueError:
        pass
    
    # String (strip quotes if present)
    return value_str.strip('"\'')


def _parse_properties(props_str: str, line_num: int) -> Dict[str, Any]:
    """Parse JSON-like properties."""
    if not props_str or props_str.strip() == '{}':
        return {}
    
    # Convert to valid JSON (allow unquoted keys)
    # station: 0.0 → "station": 0.0
    # Also handle trailing commas
    fixed = props_str.strip()
    
    # Add quotes around unquoted keys
    fixed = re.sub(r'(\w+)\s*:', r'"\1":', fixed)
    
    # Remove trailing commas before } or ]
    fixed = re.sub(r',\s*([}\]])', r'\1', fixed)
    
    try:
        return json.loads(fixed)
    except json.JSONDecodeError as e:
        raise ParseError(f"Invalid properties: {e}\nInput: {props_str}", line_num)


def _parse_derive_inputs(inputs_str: str) -> Dict[str, str]:
    """Parse DERIVE inputs: loa=hull.loa, target_ratio=5.5"""
    inputs = {}
    if not inputs_str.strip():
        return inputs
        
    for part in inputs_str.split(','):
        if '=' in part:
            key, value = part.split('=', 1)
            inputs[key.strip()] = value.strip()
    return inputs


def _collect_multiline_json(lines: List[str], start_idx: int) -> tuple:
    """Collect multi-line JSON block. Returns (json_str, lines_consumed)."""
    result = []
    depth = 0
    lines_consumed = 0
    
    for i in range(start_idx, len(lines)):
        line = lines[i]
        # Remove comments for brace counting
        clean_line = line.split('#')[0].split('//')[0]
        result.append(line)
        depth += clean_line.count('{') - clean_line.count('}')
        lines_consumed += 1
        if depth <= 0 and '{' in ''.join(result):
            break
    
    full_text = ' '.join(result)
    # Extract just the JSON part
    brace_start = full_text.find('{')
    if brace_start >= 0:
        return full_text[brace_start:], lines_consumed
    return '{}', lines_consumed


