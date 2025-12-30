#!/usr/bin/env python3
"""
Terminal Command Menu & Alias Manager

This script reads a YAML configuration file defining command categories and commands,
then presents an interactive terminal menu for users to select and execute commands.
It supports argument prompts with default values and choice selections.
"""

import sys
import yaml
import subprocess
import argparse
from simple_term_menu import TerminalMenu
import os

def clean_input(prompt: str) -> str:
    """
    Prompts user, then clears the prompt line.
    Returns the text entered by the user.
    Note: Ctrl-C will raise KeyboardInterrupt and terminate the program.
    Esc key is treated as empty input (like pressing Enter).

    Args:
        prompt (str): The prompt string to display.
    Returns:
        str: The user input, or empty string if Esc was pressed.
    """
    userInput = input(prompt)

    # Check if Esc was pressed (sends escape sequence starting with \x1b)
    if userInput.startswith('\x1b'):
        userInput = ""

    # Move cursor up one line and clear it
    sys.stdout.write("\033[A\033[K")
    sys.stdout.flush()
    return userInput

def get_argument_value(argConfig: dict) -> str:
    """
    Determines the value for an argument based on config.
    Handles 'choices' (menu) vs 'standard input' (text).

    Args:
        argConfig (dict): argument configuration with keys like 'name', 'default', 'choices'
    Returns:
        str: the value entered/selected by the user, or None if cancelled
    """
    name = argConfig.get('name', 'Argument')
    default = argConfig.get('default')
    choices = argConfig.get('choices')

    # CASE A: The argument has a strict list of choices
    if choices:
        # Convert all choices to strings for display
        choicesStr = [str(c) for c in choices]

        # If there is a default, pre-select it index-wise (optional polish)
        cursorIndex = 0
        if default and str(default) in choicesStr:
            cursorIndex = choicesStr.index(str(default))

        selectionMenu = TerminalMenu(
            choicesStr,
            title=f"Select {name}:",
            cursor_index=cursorIndex,
            raise_error_on_interrupt=True
        )
        index = selectionMenu.show()

        if index is None: return None # User hit Esc
        return choicesStr[index]

    # CASE B: Standard Text Input
    promptStr = f"  Enter {name}"
    if default is not None:
        promptStr += f" [default: {default}]: "
    else:
        promptStr += ": "

    val = clean_input(promptStr)

    # Handle cancellation
    if val is None: return None

    # Use default if input is empty
    if val.strip() == "" and default is not None:
        return str(default)

    return val

def run_command(cmdTemplate: str, argsConfig: list, continuous: bool, preSuppliedArgs: list = None):
    """Collect command arguments from user via prompts, and run the bash command.

    Args:
        cmdTemplate (str): command string with $1, $2, etc. placeholders
        argsConfig (list): list of argument configurations, each a dict with keys like 'name', 'default', 'choices'
        continuous (bool): whether to keep running after command execution to run more commands
        preSuppliedArgs (list): optional list of arguments supplied via CLI (will prompt for missing ones)

    Returns:
        None
    """
    finalCmd = cmdTemplate
    collectedArgs = []
    preSuppliedArgs = preSuppliedArgs or []

    # 1. Collect Arguments
    if argsConfig:
        for i, arg in enumerate(argsConfig, 1):
            # Use pre-supplied argument if available, otherwise prompt
            if i - 1 < len(preSuppliedArgs):
                val = preSuppliedArgs[i - 1]
            else:
                val = get_argument_value(arg)

            if val is None:
                return # User cancelled

            collectedArgs.append(val)

            # Replace $1, $2, etc. in the command string
            placeholder = f"${i}"
            if placeholder in finalCmd:
                finalCmd = finalCmd.replace(placeholder, val)

    # If the command didn't use $ vars, append args to the end
    if "$" not in cmdTemplate and collectedArgs:
        finalCmd += " " + " ".join(collectedArgs)

    # 2. Execute
    print(f"\n> Executing: {finalCmd}")
    try:
        subprocess.run(finalCmd, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")

    if continuous:
        clean_input("\nPress Enter to return to menu...")
    else:
        print("\nCommand execution completed.")
        sys.exit(0)

def find_command_by_name(data: dict, command_name: str):
    """
    Search for a command by name across all categories.

    Args:
        data (dict): The commands data structure
        command_name (str): The name of the command to find

    Returns:
        dict or None: The command dict if found, None otherwise
    """
    for category, commands in data.items():
        for cmd in commands:
            if cmd['name'] == command_name:
                return cmd
    return None

def load_commands():
    """Load commands from YAML files."""
    # Load commands.yaml
    try:
        with open("commands.yaml", 'r') as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        print("Error: commands.yaml not found.")
        return {}
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)

    # Load custom.yaml if it exists and merge with commands.yaml
    try:
        with open("custom.yaml", 'r') as f:
            customData = yaml.safe_load(f)
            if customData:
                for category, commands in customData.items():
                    if category in data:
                        # Merge commands into existing category
                        data[category].extend(commands)
                    else:
                        # Add new category
                        data[category] = commands
    except FileNotFoundError:
        pass  # custom.yaml is optional
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)

    return data

def generate_bash_completion():
    """Generate bash completion script"""
    commands = []
    for category_data in load_commands().values():
        commands.extend([cmd['name'] for cmd in category_data])

    completion_script = f"""# Bash completion for commander.py
_commander_completions() {{
    local cur="${{COMP_WORDS[COMP_CWORD]}}"

    if [ $COMP_CWORD -eq 1 ]; then
        COMPREPLY=( $(compgen -W "{' '.join(commands)}" -- ${{cur}}) )
        return 0
    fi
}}

complete -F _commander_completions commander.py
complete -F _commander_completions ./commander.py
"""

    completion_file = os.path.join(os.path.expanduser('~'), '.commander-completion.bash')
    with open(completion_file, 'w') as f:
        f.write(completion_script)

    print(f"Bash completion script generated: {completion_file}")
    print(f"\nTo enable completion, add this line to ~/.bashrc:")
    print(f"  source ~/.commander-completion.bash")
    print(f"\nThen reload: source ~/.bashrc")
    print(f"\nTo update completions after adding commands, re-run this and then:")
    print(f"  source ~/.commander-completion.bash  (or open a new terminal)")

def generate_bash_aliases():
    """Generate bash aliases file"""
    import re

    data = load_commands()
    alias_file = os.path.join(os.path.expanduser('~'), '.bash_aliascore')

    # First pass: collect all function names that might conflict
    functions_to_unalias = []
    for category, items in data.items():
        for item in items:
            name = item['name']
            cmd = item['cmd']
            cmd_type = item.get('type')
            if not cmd_type:
                if re.search(r'\$\d+', cmd):
                    cmd_type = 'function'
                else:
                    cmd_type = 'alias'
            if cmd_type == 'function':
                functions_to_unalias.append(name)

    with open(alias_file, 'w') as out:
        out.write("# AUTO-GENERATED FILE. DO NOT EDIT DIRECTLY.\n")
        out.write("# Edit commands.yaml or custom.yaml instead.\n\n")

        # Unalias all functions at the top to avoid conflicts
        if functions_to_unalias:
            out.write("# Remove any existing aliases that would conflict with functions\n")
            for func_name in functions_to_unalias:
                out.write(f"unalias {func_name} 2>/dev/null || true\n")
            out.write("\n")

        for category, items in data.items():
            out.write(f"\n#* {category}\n")

            for item in items:
                name = item['name']
                cmd = item['cmd']
                desc = item.get('desc', '')

                # Auto-detect type: if command has $1, $2, etc., it's a function
                cmd_type = item.get('type')
                if not cmd_type:
                    # Check if command uses positional parameters
                    if re.search(r'\$\d+', cmd):
                        cmd_type = 'function'
                    else:
                        cmd_type = 'alias'

                # Format description as inline comment
                desc_suffix = f'  # {desc}' if desc else ''

                if cmd_type == 'alias':
                    # Escape single quotes in command for bash alias
                    cmd_escaped = cmd.replace("'", "'\"'\"'")
                    out.write(f"alias {name}='{cmd_escaped}'{desc_suffix}\n")
                elif cmd_type == 'function':
                    # Strip trailing semicolon to avoid double semicolon in function
                    cmd_cleaned = cmd.rstrip(';').rstrip()
                    out.write(f"{name}() {{ {cmd_cleaned}; }}{desc_suffix}\n")

    print(f"Bash aliases file generated: {alias_file}")
    print(f"\nTo enable aliases, add this line to ~/.bashrc:")
    print(f"  source ~/.bash_aliascore")
    print(f"\nThen reload: source ~/.bashrc")
    print(f"\nTo update aliases after adding commands, re-run this and then:")
    print(f"  source ~/.bash_aliascore  (or open a new terminal)")

def generate_all():
    """Generate both bash completion and aliases"""
    print("=== Generating Bash Completion ===")
    generate_bash_completion()
    print("\n=== Generating Bash Aliases ===")
    generate_bash_aliases()
    print("\n=== Done! ===")
    print("\nAdd these lines to ~/.bashrc:")
    print("  source ~/.commander-completion.bash")
    print("  source ~/.bash_aliascore")
    print("\nThen reload: source ~/.bashrc")

def main():
    """
    Run the commander program. Supports continuous interactive mode or single command mode.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Terminal Command Menu & Alias Manager')
    parser.add_argument('-c', '--continuous', action='store_true',
                        help='Run in continuous interactive mode (default: single command mode)')
    parser.add_argument('command', nargs='?', default=None,
                        help='Command name to execute directly without menu')
    parser.add_argument('cmdargs', nargs='*',
                        help='Arguments for the command')
    parser.add_argument('--generate-completion', action='store_true',
                        help='Generate bash completion script')
    parser.add_argument('--generate-aliases', action='store_true',
                        help='Generate bash aliases file')
    parser.add_argument('--generate-all', action='store_true',
                        help='Generate both completion script and aliases file')
    args = parser.parse_args()

    continuousMode = args.continuous
    directCommand = args.command
    commandArgs = args.cmdargs

    if args.generate_completion:
        generate_bash_completion()
        sys.exit(0)

    if args.generate_aliases:
        generate_bash_aliases()
        sys.exit(0)

    if args.generate_all:
        generate_all()
        sys.exit(0)

    data = load_commands()

    # If a direct command was specified, execute it and exit
    if directCommand:
        cmd = find_command_by_name(data, directCommand)
        if cmd:
            run_command(cmd['cmd'], cmd.get('args', []), False, commandArgs)
        else:
            print(f"Error: Command '{directCommand}' not found.")
            print("\nAvailable commands:")
            for category, commands in data.items():
                print(f"\n{category}:")
                for c in commands:
                    print(f"  - {c['name']}: {c.get('desc', '')}")
            sys.exit(1)
        return

    categories = list(data.keys()) + ["Exit"]

    try:
        while True:
            # --- Level 1: Categories ---
            catMenu = TerminalMenu(categories, title="Select Category", raise_error_on_interrupt=True)
            catIndex = catMenu.show()

            if catIndex is None:
                print("\nExiting...")
                break
            selectedCat = categories[catIndex]
            if selectedCat == "Exit":
                print("\nExiting...")
                break

            # Get items for this category
            items = data[selectedCat]

            # Format Labels - show description on same line as command name
            itemLabels = [f"{i['name']} - {i.get('desc', '')}" for i in items]
            itemLabels.append("Back")

            while True:
                # --- Level 2: Commands ---
                cmdMenu = TerminalMenu(itemLabels, title=f"Category: {selectedCat}", raise_error_on_interrupt=True)
                cmdIndex = cmdMenu.show()

                if cmdIndex is None or itemLabels[cmdIndex] == "Back":
                    break

                selectedItem = items[cmdIndex]

                # Pass the structured 'args' list directly and continuous mode flag
                run_command(selectedItem['cmd'], selectedItem.get('args', []), continuousMode)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)

if __name__ == "__main__":
    main()
