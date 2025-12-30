# Terminal Command Menu & Alias Manager

## Project Overview
This project provides a unified system for managing, organizing, and executing complex shell commands. Instead of maintaining a messy `.bashrc` or remembering obscure command flags, you define your commands once in a structured **YAML** file.

This "Source of Truth" drives two interfaces:
1.  **Interactive Menu (`commander.py`):** A visual, scrollable terminal window to browse commands, input arguments (with defaults/dropdowns), and execute them immediately.
2.  **Native Shell Aliases (`generate_alias_file.py`):** A generator that converts your YAML config into a standard `.bash_aliases` file for native shell usage.

## File Structure & Purpose

### 1. `commands.yaml` (The Source of Truth)
This is the master configuration file. It contains command categories, descriptions, the actual shell commands, and structured arguments.

**Features:**
*   **Categories:** Organize commands (e.g., "Networking", "Docker").
*   **Arguments:** Define inputs (`$1`, `$2`) with optional defaults and distinct choice lists.
*   **Documentation:** Every command has a description that appears in the menu.

### 1.5 `custom.yaml` (Optional Personal Commands)
An optional configuration file for your personal commands that won't be tracked in version control. This file follows the same format as `commands.yaml`.

**How it works:**
*   Commands from `custom.yaml` are automatically merged with `commands.yaml` at runtime.
*   If a category exists in both files, the commands are combined.
*   If a category only exists in `custom.yaml`, it's added as a new category.
*   The file is already added to `.gitignore`, so your personal commands stay private.

**Example `custom.yaml`:**
```yaml
Personal:
  - name: myserver
    cmd: "ssh user@myserver.com"
    desc: "Connect to my server"

Network Stuff:
  - name: ping_home
    cmd: "ping 192.168.1.100"
    desc: "Ping my home server"
```
In this example, "Personal" would be a new category, while "ping_home" would be added to the existing "Network Stuff" category.

### 2. `commander.py` (The Interactive UI)
A Python script utilizing `simple-term-menu` to create a "window-like" experience inside the terminal.

**Key Functions:**
*   **Category Navigation:** Browse commands by group.
*   **Dynamic Prompts:** Detects if a command needs arguments.
    *   If `choices` are defined: Opens a sub-menu to pick an option.
    *   If `default` is defined: Pre-fills the prompt (press Enter to accept).
    *   If neither: Forces the user to type input.
*   **Clean Output:** Uses ANSI escape codes to erase prompts after entry, keeping the terminal history clean.

### 3. `generate_alias_file.py` (The Alias Generator)
A utility script that parses `commands.yaml` and exports a standard Bash alias file.

**Operation:**
*   Converts `type: function` entries into Bash functions (`name() { ... }`).
*   Converts simple commands into Bash aliases (`alias name='...'`).
*   Embeds descriptions as comments in the generated file.

---

## Configuration Guide (`commands.yaml`)

The system relies on a specific YAML structure.

### Basic Command
```yaml
System:
  - name: updates
    cmd: "sudo apt update && sudo apt upgrade -y"
    desc: "Update system packages"
```

### Command with Arguments & Defaults
Use `$1`, `$2`, etc., in the `cmd` string to mark where arguments go.

```yaml
Networking:
  - name: ping_host
    cmd: "ping -c $1 $2"
    desc: "Ping a remote host"
    args:
      - name: "Count"
        default: 3       # Pressing Enter uses "3"
      - name: "Target"   # No default; user must type input
```

### Command with Dropdown Choices
If you provide `choices`, the menu will force the user to pick from a list.

```yaml
Docker:
  - name: container_log
    cmd: "docker logs $1"
    desc: "View logs for a specific container"
    args:
      - name: "Container"
        choices: ["web_app", "db_server", "redis_cache"]
```

---

## Installation & Usage

### 1. Prerequisites
This project requires Python 3 and the following libraries:
```bash
pip install pyyaml simple-term-menu
```
*Note: `simple-term-menu` supports Linux and macOS only.*

### 2. Running the Menu

#### Interactive Mode (Default)
To launch the interactive window:
```bash
python commander.py
```

#### Direct Command Execution
You can also run commands directly without the menu:
```bash
# Run a command by name (will prompt for any required arguments)
python commander.py ipaddr

# Provide all arguments on the command line (no prompts)
python commander.py ping google.com

# Provide some arguments (will prompt for missing ones)
python commander.py ddcopy /dev/sda1
# (will then prompt for "Output File")
```

#### Continuous Mode
Add the `-c` or `--continuous` flag to stay in interactive mode after command execution:
```bash
# Interactive menu with continuous mode
python commander.py -c

# Direct command with continuous mode
python commander.py -c ping 8.8.8.8
```

**Command Line Syntax:**
```bash
python commander.py [-c] [command_name] [arg1] [arg2] ...
```

### 3. Bash Tab Completion (Optional but Recommended)

Enable tab completion for command names to speed up command execution:

#### Generate the completion script:
```bash
python commander.py --generate-completion
```

This creates `~/.commander-completion.bash` in your home directory. The script includes all commands from both `commands.yaml` and `custom.yaml`.

#### Enable completion in your shell (one-time setup):
Add this line to your `~/.bashrc`:
```bash
source ~/.commander-completion.bash
```

Then reload your bash configuration:
```bash
source ~/.bashrc
```

#### Usage:
Now you can use tab completion:
```bash
python commander.py pi<TAB>
# Auto-completes to: python commander.py ping

python commander.py ip<TAB>
# Shows: ipaddr  iplink  iproute  ipshow
```

#### Updating completions:
When you add new commands to `commands.yaml` or `custom.yaml`, regenerate the completion script:
```bash
python commander.py --generate-completion
```

Then reload it in your current shell (or just open a new terminal):
```bash
source ~/.commander-completion.bash
```

### 4. Bash Aliases Generation (Optional)

Generate a traditional bash aliases file from your commands:

#### Generate the aliases file:
```bash
python commander.py --generate-aliases
```

This creates `~/.bash_aliascore` in your home directory with all commands from both `commands.yaml` and `custom.yaml`. Commands with arguments (`$1`, `$2`, etc.) are created as bash functions, while simple commands become aliases.

#### Enable aliases in your shell (one-time setup):
Add this line to your `~/.bashrc`:
```bash
source ~/.bash_aliascore
```

Then reload:
```bash
source ~/.bashrc
```

#### Usage:
Now you can use the commands directly in your shell:
```bash
ll          # Lists files
ping google.com  # Pings Google
```

#### Updating aliases:
When you add new commands, regenerate:
```bash
python commander.py --generate-aliases
source ~/.bash_aliascore  # or open a new terminal
```

### 5. Generate Everything at Once

To generate both completion and aliases in one command:
```bash
python commander.py --generate-all
```

This will create both `~/.commander-completion.bash` and `~/.bash_aliascore`.

**One-time setup:** Add both to your `~/.bashrc`:
```bash
source ~/.commander-completion.bash
source ~/.bash_aliascore
```


---

## Workflow Diagram

```text
[ commands.yaml ]  <-- YOU EDIT THIS
       |
       +-------------------------+
       |                         |
       v                         v
[ commander.py ]      [ generate_alias_file.py ]
       |                         |
       v                         v
  Interactive           [ .bash_aliases_gen ]
 Terminal Menu                   |
       |                         v
  Executes Cmds            Native Shell
   Directly              (alias name=...)
```
