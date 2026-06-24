#!/usr/bin/env python3
"""
Generate plugin documentation by scanning all plugins in the repository.

This script scans the plugins directory, reads plugin metadata and skill files,
and generates a markdown documentation section listing all available plugins and skills.
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class PluginInfo:
    """Information about a plugin."""
    
    def __init__(self, name: str, description: str, version: str):
        self.name = name
        self.description = description
        self.version = version
        self.skills = []

    def add_skill(self, skill_name: str, description: str):
        """Add a skill to this plugin."""
        self.skills.append({
            'name': skill_name,
            'description': description
        })


def parse_frontmatter(content: str) -> Dict[str, str]:
    """Parse YAML frontmatter from a markdown file."""
    frontmatter = {}
    
    # Match frontmatter between --- markers
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if match:
        frontmatter_text = match.group(1)
        
        # Parse simple YAML key-value pairs
        for line in frontmatter_text.split('\n'):
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                frontmatter[key.strip()] = value.strip()
    
    return frontmatter


def get_plugin_info(plugin_dir: Path) -> PluginInfo:
    """Extract plugin information from plugin.json and command files."""
    
    # Read plugin metadata
    plugin_json_path = plugin_dir / '.claude-plugin' / 'plugin.json'
    if not plugin_json_path.exists():
        return None
    
    with open(plugin_json_path, 'r') as f:
        plugin_data = json.load(f)

    plugin_info = PluginInfo(
        name=plugin_data.get('name', plugin_dir.name),
        description=plugin_data.get('description', ''),
        version=plugin_data.get('version', '0.0.0')
    )

    # Scan skills
    skills_dir = plugin_dir / 'skills'
    if skills_dir.exists():
        skill_files = sorted(skills_dir.glob('*/SKILL.md'))

        for skill_file in skill_files:
            with open(skill_file, 'r') as f:
                content = f.read()

            frontmatter = parse_frontmatter(content)
            skill_name = frontmatter.get('name', skill_file.parent.name)

            plugin_info.add_skill(
                skill_name=skill_name,
                description=frontmatter.get('description', '')
            )

    return plugin_info


def generate_plugin_docs(plugins_dir: Path) -> str:
    """Generate markdown documentation for all plugins."""
    
    # Collect all plugins
    plugins = []
    
    for plugin_dir in sorted(plugins_dir.iterdir()):
        if not plugin_dir.is_dir():
            continue
        
        plugin_info = get_plugin_info(plugin_dir)
        if plugin_info and plugin_info.skills:
            plugins.append(plugin_info)
    
    # Generate markdown
    lines = []
    lines.append("# Available Plugins")
    lines.append("")
    lines.append("This document lists all available Claude Code plugins and their skills in this repository.")
    lines.append("")

    # Generate table of contents
    for plugin in plugins:
        plugin_title = plugin.name.replace('-', ' ').title()
        # Create anchor link (GitHub converts headers to lowercase with hyphens)
        anchor = plugin_title.lower().replace(' ', '-') + '-plugin'
        lines.append(f"- [{plugin_title}](#{anchor})")
    lines.append("")

    for plugin in plugins:
        # Plugin header
        lines.append(f"### {plugin.name.replace('-', ' ').title()} Plugin")
        lines.append("")
        
        if plugin.description:
            lines.append(plugin.description)
            lines.append("")
        
        # Skills list
        if plugin.skills:
            lines.append("**Skills:**")
            for skill in plugin.skills:
                lines.append(f"- **`/{skill['name']}`** - {skill['description']}")
            lines.append("")

        # Link to plugin README if it exists
        readme_path = plugins_dir / plugin.name / 'README.md'
        if readme_path.exists():
            lines.append(f"See [plugins/{plugin.name}/README.md](plugins/{plugin.name}/README.md) for detailed documentation.")
            lines.append("")
    
    return '\n'.join(lines)


def write_plugins_file(plugins_path: Path, plugins_content: str) -> None:
    """Write the PLUGINS.md file with plugin documentation."""
    
    with open(plugins_path, 'w') as f:
        f.write(plugins_content)


def main():
    """Main entry point."""
    
    # Determine repository root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    
    plugins_dir = repo_root / 'plugins'
    plugins_path = repo_root / 'PLUGINS.md'
    
    if not plugins_dir.exists():
        print(f"Error: Plugins directory not found: {plugins_dir}", file=sys.stderr)
        sys.exit(1)
    
    print("Scanning plugins...")
    plugins_docs = generate_plugin_docs(plugins_dir)
    
    print("Writing PLUGINS.md...")
    write_plugins_file(plugins_path, plugins_docs)
    
    print("✓ Plugin documentation updated successfully in PLUGINS.md!")


if __name__ == '__main__':
    main()

