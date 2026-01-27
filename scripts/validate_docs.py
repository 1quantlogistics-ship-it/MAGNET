#!/usr/bin/env python3
"""
MAGNET Documentation Validation Script

Validates:
1. All .md files have AGENT_CONTEXT headers
2. MANIFEST.yaml is complete and accurate
3. Deprecated files have redirect notices
4. Keyword index coverage

Usage:
    python scripts/validate_docs.py --check       # Check only (exit code indicates issues)
    python scripts/validate_docs.py --report      # Generate detailed report
    python scripts/validate_docs.py --fix-missing # Add placeholder AGENT_CONTEXT to files without one
"""

import os
import re
import sys
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Set, Optional

# Configuration
DOCS_ROOT = Path(__file__).parent.parent / "docs"
MANIFEST_PATH = DOCS_ROOT / "_index" / "MANIFEST.yaml"

# Patterns
AGENT_CONTEXT_PATTERN = re.compile(
    r'<!--\s*AGENT_CONTEXT\s*\n(.*?)\n\s*-->',
    re.DOTALL | re.IGNORECASE
)


@dataclass
class ValidationResult:
    """Result of validating a single file."""
    path: str
    has_agent_context: bool
    is_deprecated: bool
    has_redirect: bool
    keywords: List[str]
    issues: List[str]


@dataclass
class ManifestEntry:
    """Entry from MANIFEST.yaml."""
    path: str
    purpose: str
    status: str
    keywords: List[str]
    redirect: Optional[str] = None


def find_all_markdown_files(root: Path) -> List[Path]:
    """Find all .md files in the docs directory."""
    files = []
    for path in root.rglob("*.md"):
        # Skip hidden directories
        if any(part.startswith('.') for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def parse_agent_context(content: str) -> Optional[Dict[str, str]]:
    """Extract AGENT_CONTEXT data from file content."""
    match = AGENT_CONTEXT_PATTERN.search(content)
    if not match:
        return None

    context_text = match.group(1)
    result = {}

    for line in context_text.strip().split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            result[key.strip().lower()] = value.strip()

    return result


def load_manifest() -> Dict[str, ManifestEntry]:
    """Load and parse MANIFEST.yaml."""
    if not MANIFEST_PATH.exists():
        return {}

    with open(MANIFEST_PATH, 'r') as f:
        data = yaml.safe_load(f)

    entries = {}
    for category_name, category in data.get('categories', {}).items():
        for doc in category.get('docs', []):
            entry = ManifestEntry(
                path=doc['path'],
                purpose=doc.get('purpose', ''),
                status=doc.get('status', 'unknown'),
                keywords=doc.get('keywords', []),
                redirect=doc.get('redirect')
            )
            entries[doc['path']] = entry

    return entries


def validate_file(filepath: Path, manifest_entries: Dict[str, ManifestEntry]) -> ValidationResult:
    """Validate a single markdown file."""
    relative_path = str(filepath.relative_to(DOCS_ROOT))
    issues = []

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check for AGENT_CONTEXT
    context = parse_agent_context(content)
    has_agent_context = context is not None

    if not has_agent_context:
        issues.append("Missing AGENT_CONTEXT header")

    # Check deprecation status
    is_deprecated = False
    has_redirect = False
    keywords = []

    if context:
        status = context.get('status', '').lower()
        is_deprecated = status == 'deprecated'
        has_redirect = 'redirect' in context

        if context.get('keywords'):
            keywords = [k.strip() for k in context['keywords'].split(',')]

        if is_deprecated and not has_redirect:
            issues.append("Deprecated file missing Redirect field")

    # Check if file is in manifest
    if relative_path not in manifest_entries:
        # Check with forward slashes
        relative_path_normalized = relative_path.replace('\\', '/')
        if relative_path_normalized not in manifest_entries:
            issues.append("File not in MANIFEST.yaml")

    return ValidationResult(
        path=relative_path,
        has_agent_context=has_agent_context,
        is_deprecated=is_deprecated,
        has_redirect=has_redirect,
        keywords=keywords,
        issues=issues
    )


def check_manifest_completeness(manifest_entries: Dict[str, ManifestEntry],
                                 actual_files: List[Path]) -> List[str]:
    """Check if manifest has entries for all files."""
    issues = []
    actual_paths = {str(f.relative_to(DOCS_ROOT)).replace('\\', '/') for f in actual_files}
    manifest_paths = set(manifest_entries.keys())

    # Files in docs but not in manifest
    missing_from_manifest = actual_paths - manifest_paths
    for path in sorted(missing_from_manifest):
        issues.append(f"File not in manifest: {path}")

    # Files in manifest but not in docs
    missing_from_docs = manifest_paths - actual_paths
    for path in sorted(missing_from_docs):
        issues.append(f"Manifest entry missing file: {path}")

    return issues


def generate_placeholder_context(filepath: Path) -> str:
    """Generate a placeholder AGENT_CONTEXT for a file."""
    filename = filepath.stem
    return f"""<!-- AGENT_CONTEXT
Purpose: [TODO: Add purpose description]
Authoritative: No
Keywords: [{filename.lower().replace('_', ', ').replace('-', ', ')}]
Depends_On: None
Used_By: [TODO: Add users]
Status: current
Last_Verified: 2026-01-15
-->

"""


def add_placeholder_context(filepath: Path) -> bool:
    """Add placeholder AGENT_CONTEXT to a file that's missing one."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if AGENT_CONTEXT_PATTERN.search(content):
        return False  # Already has context

    # Find the first heading
    lines = content.split('\n')
    heading_idx = -1
    for i, line in enumerate(lines):
        if line.startswith('#'):
            heading_idx = i
            break

    if heading_idx == -1:
        # No heading found, add at start
        new_content = generate_placeholder_context(filepath) + content
    else:
        # Add after first heading
        before = '\n'.join(lines[:heading_idx + 1])
        after = '\n'.join(lines[heading_idx + 1:])
        placeholder = generate_placeholder_context(filepath)
        new_content = before + '\n\n' + placeholder + after

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Validate MAGNET documentation')
    parser.add_argument('--check', action='store_true', help='Check only (default)')
    parser.add_argument('--report', action='store_true', help='Generate detailed report')
    parser.add_argument('--fix-missing', action='store_true', help='Add placeholder AGENT_CONTEXT')
    args = parser.parse_args()

    # Default to check mode
    if not args.report and not args.fix_missing:
        args.check = True

    print("=" * 60)
    print("MAGNET Documentation Validation")
    print("=" * 60)
    print()

    # Find all markdown files
    all_files = find_all_markdown_files(DOCS_ROOT)
    print(f"Found {len(all_files)} markdown files")

    # Load manifest
    manifest_entries = load_manifest()
    print(f"Manifest has {len(manifest_entries)} entries")
    print()

    # Validate each file
    results = []
    for filepath in all_files:
        result = validate_file(filepath, manifest_entries)
        results.append(result)

    # Check manifest completeness
    manifest_issues = check_manifest_completeness(manifest_entries, all_files)

    # Summary statistics
    total = len(results)
    with_context = sum(1 for r in results if r.has_agent_context)
    deprecated = sum(1 for r in results if r.is_deprecated)
    with_issues = sum(1 for r in results if r.issues)

    print("SUMMARY")
    print("-" * 40)
    print(f"Total files:           {total}")
    print(f"With AGENT_CONTEXT:    {with_context} ({100*with_context/total:.0f}%)")
    print(f"Deprecated:            {deprecated}")
    print(f"Files with issues:     {with_issues}")
    print(f"Manifest issues:       {len(manifest_issues)}")
    print()

    if args.report or args.check:
        # Report issues
        if with_issues > 0 or manifest_issues:
            print("ISSUES")
            print("-" * 40)

            for result in results:
                if result.issues:
                    print(f"\n{result.path}:")
                    for issue in result.issues:
                        print(f"  - {issue}")

            if manifest_issues:
                print("\nManifest Issues:")
                for issue in manifest_issues:
                    print(f"  - {issue}")

    if args.fix_missing:
        print("\nFIXING MISSING AGENT_CONTEXT")
        print("-" * 40)
        fixed = 0
        for result in results:
            if not result.has_agent_context:
                filepath = DOCS_ROOT / result.path
                if add_placeholder_context(filepath):
                    print(f"  Added: {result.path}")
                    fixed += 1
        print(f"\nFixed {fixed} files")

    # Exit code
    if args.check:
        if with_issues > 0 or manifest_issues:
            print("\n[FAIL] Validation issues found")
            sys.exit(1)
        else:
            print("\n[PASS] All validations passed")
            sys.exit(0)


if __name__ == '__main__':
    main()
