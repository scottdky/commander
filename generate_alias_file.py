#!/usr/bin/env python3
"""
This program takes a yaml file that defines bash aliases and functions. After loading
the definitions, it creates a bash_aliases file with them. This yaml file is also
intended to be used with a menu program that executes the bash commands.
"""

import yaml

def generate_bash(yaml_file, output_file):
    with open(yaml_file, 'r') as f:
        data = yaml.safe_load(f)

    with open(output_file, 'w') as out:
        out.write("# AUTO-GENERATED FILE. DO NOT EDIT DIRECTLY.\n")
        out.write(f"# Edit {yaml_file} instead.\n\n")

        for category, items in data.items():
            out.write(f"\n#* {category}\n")
            
            for item in items:
                name = item['name']
                cmd = item['cmd']
                desc = item.get('desc', '')
                
                # Write the comment description
                if desc:
                    out.write(f"# {desc}\n")

                if item['type'] == 'alias':
                    # Bash aliases usually append args automatically at the end
                    out.write(f"alias {name}='{cmd}'\n")
                
                elif item['type'] == 'function':
                    # Functions explicitly handle $1, $2, etc.
                    out.write(f"{name}() {{ {cmd}; }}\n")

    print(f"Successfully generated {output_file}")

if __name__ == "__main__":
    generate_bash("commands.yaml", "bash_aliases")
