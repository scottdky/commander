#!/usr/bin/env python3
"""
Package Installation Script for Commander

This script installs packages required by commands defined in commands.yaml.
It reads packages.yaml to determine installation methods and executes them.
"""

import yaml
import subprocess
import sys
import re

def load_yaml(filename):
    """Load YAML file"""
    try:
        with open(filename, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: {filename} not found.")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing {filename}: {e}")
        sys.exit(1)

def find_commands_in_yaml(commands_data):
    """Extract all command names used in commands.yaml"""
    used_commands = set()
    
    for category, items in commands_data.items():
        for item in items:
            cmd_str = item.get('cmd', '')
            # Extract command names (first word of each command or after pipes/semicolons)
            words = re.findall(r'\b[a-z][\w-]+\b', cmd_str.lower())
            used_commands.update(words)
    
    return used_commands

def check_command_installed(cmd):
    """Check if a command is already installed"""
    try:
        subprocess.run(['which', cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def check_package_installed(package):
    """Check if an apt package is installed"""
    try:
        result = subprocess.run(
            ['dpkg', '-l', package],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.returncode == 0 and 'ii' in result.stdout
    except:
        return False

def main():
    print("=== Commander Package Installer ===\n")
    
    # Load configuration files
    print("Loading configuration files...")
    packages_config = load_yaml('packages.yaml')
    commands_data = load_yaml('commands.yaml')
    
    # Try to load custom.yaml if it exists
    try:
        custom_data = load_yaml('custom.yaml')
        if custom_data:
            for category, commands in custom_data.items():
                if category in commands_data:
                    commands_data[category].extend(commands)
                else:
                    commands_data[category] = commands
    except:
        pass  # custom.yaml is optional
    
    # Find commands used in YAML files
    used_commands = find_commands_in_yaml(commands_data)
    
    # Categorize packages by installation method
    apt_packages = set()
    custom_installs = []
    manual_installs = []
    already_installed = []
    
    command_mappings = packages_config.get('commands', {})
    
    for cmd_name in used_commands:
        if cmd_name in command_mappings:
            mapping = command_mappings[cmd_name]
            package = mapping.get('package')
            method = mapping.get('method')
            
            # Check if already installed
            if check_command_installed(cmd_name):
                already_installed.append(cmd_name)
                continue
            
            if method == 'apt':
                apt_packages.add(package)
            elif method == 'custom':
                custom_installs.append({
                    'command': cmd_name,
                    'package': package,
                    'commands': mapping.get('commands', []),
                    'notes': mapping.get('notes', '')
                })
            elif method == 'manual':
                manual_installs.append({
                    'command': cmd_name,
                    'package': package,
                    'url': mapping.get('url', ''),
                    'notes': mapping.get('notes', '')
                })
    
    # Display summary
    print(f"\nFound {len(used_commands)} unique commands in YAML files")
    print(f"  - {len(already_installed)} already installed")
    print(f"  - {len(apt_packages)} to install via apt")
    print(f"  - {len(custom_installs)} to install via custom commands")
    print(f"  - {len(manual_installs)} require manual installation")
    
    if already_installed:
        print(f"\n✓ Already installed: {', '.join(sorted(already_installed))}")
    
    # Install apt packages
    if apt_packages:
        print(f"\n=== APT Packages ===")
        print(f"The following packages will be installed:")
        for pkg in sorted(apt_packages):
            installed = "✓" if check_package_installed(pkg) else " "
            print(f"  [{installed}] {pkg}")
        
        response = input("\nInstall these packages? [y/N]: ").strip().lower()
        if response == 'y':
            print("\nInstalling apt packages...")
            cmd = ['sudo', 'apt-get', 'install', '-y'] + list(apt_packages)
            try:
                subprocess.run(cmd, check=True)
                print("✓ APT packages installed successfully")
            except subprocess.CalledProcessError:
                print("✗ Error installing apt packages")
        else:
            print("Skipped apt installation")
    
    # Custom installations
    if custom_installs:
        print(f"\n=== Custom Installations ===")
        for install in custom_installs:
            print(f"\n{install['command']} → {install['package']}")
            if install['notes']:
                print(f"  Note: {install['notes']}")
            print("  Commands:")
            for cmd in install['commands']:
                print(f"    {cmd}")
            
            response = input(f"  Execute these commands? [y/N]: ").strip().lower()
            if response == 'y':
                for cmd in install['commands']:
                    print(f"  Running: {cmd}")
                    try:
                        subprocess.run(cmd, shell=True, check=True)
                    except subprocess.CalledProcessError:
                        print(f"  ✗ Error executing: {cmd}")
                print(f"✓ {install['package']} installed")
            else:
                print(f"  Skipped {install['package']}")
    
    # Manual installations
    if manual_installs:
        print(f"\n=== Manual Installation Required ===")
        for install in manual_installs:
            print(f"\n{install['command']} → {install['package']}")
            if install['url']:
                print(f"  URL: {install['url']}")
            if install['notes']:
                print(f"  Note: {install['notes']}")
    
    print("\n=== Installation Complete ===")

if __name__ == "__main__":
    main()
