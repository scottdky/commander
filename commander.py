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

def run_command(cmdTemplate: str, argsConfig: list, continuous: bool):
    """Collect command arguments from user via prompts, and run the bash command.

    Args:
        cmdTemplate (str): command string with $1, $2, etc. placeholders
        argsConfig (list): list of argument configurations, each a dict with keys like 'name', 'default', 'choices'
        continuous (bool): whether to keep running after command execution to run more commands

    Returns:
        None
    """
    finalCmd = cmdTemplate
    collectedArgs = []

    # 1. Collect Arguments
    if argsConfig:
        for i, arg in enumerate(argsConfig, 1):
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

def main():
    """
    Run the commander program. Supports continuous interactive mode or single command mode.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Terminal Command Menu & Alias Manager')
    parser.add_argument('-c', '--continuous', action='store_true',
                        help='Run in continuous interactive mode (default: single command mode)')
    args = parser.parse_args()

    continuousMode = args.continuous

    # Load commands.yaml
    try:
        with open("commands.yaml", 'r') as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        print("Error: commands.yaml not found.")
        return
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
