import os
import shutil


# Every command receives its arguments as a list (without the command name).
# Example: "cp a.txt b.txt"  ->  copyPath(["a.txt", "b.txt"])
# With no arguments the list is empty: []


def clear(path=None):
    os.system("cls" if os.name == "nt" else "clear")
    return True


def getCwd(path=None):
    print(os.getcwd())
    return True


def makeDir(path=None):
    """Create a directory. Usage: mkdir <name>"""
    try:
        if not path or not path[0]:
            print("Error: directory name is required")
            return False

        os.mkdir(path[0])
        return True

    except OSError as error:
        print(f"Error: {error}")
        return False


def changeDir(path=None):
    """Change directory. Usage: cd <path>"""
    try:
        if not path or not path[0]:
            print("Error: path is required")
            return False

        os.chdir(path[0])
        print(os.getcwd())
        return True

    except OSError as error:
        print(f"Error: {error}")
        return False


def _format_size(size):
    if size < 1024:
        return f"{size} B"
    if size < 1024 ** 2:
        return f"{size / 1024:.2f} KB"
    if size < 1024 ** 3:
        return f"{size / (1024 ** 2):.2f} MB"
    return f"{size / (1024 ** 3):.2f} GB"


def listDir(path=None):
    """List directory contents. Usage: ls [directory]"""
    try:
        target = path[0] if path and path[0] else os.getcwd()

        with os.scandir(target) as entries:
            print(f"\nDirectory: {target}\n")
            print(f"{'Name':<35} {'Size':<15} {'Type'}")
            print("-" * 65)

            for entry in sorted(entries, key=lambda e: (not e.is_dir(), e.name.casefold())):
                if entry.is_dir():
                    item_type = "<DIR>"
                    size = "-"
                else:
                    item_type = os.path.splitext(entry.name)[1] or "<FILE>"
                    try:
                        size = _format_size(entry.stat().st_size)
                    except OSError:
                        size = "?"

                print(f"{entry.name:<35} {size:<15} {item_type}")

        return True

    except OSError as error:
        print(f"Error: {error}")
        return False


def moveDir(path=None):
    """Move a file or folder. Usage: mvdir <source> <destination>"""
    try:
        if not path or len(path) < 2 or not path[0] or not path[1]:
            print("Error: source and destination are required")
            return False

        shutil.move(path[0], path[1])
        return True

    except (OSError, shutil.Error) as error:
        print(f"Error: {error}")
        return False


def reNameDir(path=None):
    """Rename a file or folder. Usage: rename <old> <new>"""
    try:
        if not path or len(path) < 2 or not path[0] or not path[1]:
            print("Error: old name and new name are required")
            return False

        os.rename(path[0], path[1])
        return True

    except OSError as error:
        print(f"Error: {error}")
        return False


def removeFile(path=None):
    """Remove one file. Usage: rm <file>"""
    try:
        if not path or not path[0]:
            print("Error: file path is required")
            return False

        target = path[0]
        if os.path.isdir(target):
            print("Error: target is a directory; use rmdir for an empty directory")
            return False

        os.remove(target)
        print(f"File removed: {target}")
        return True

    except OSError as error:
        print(f"Error: {error}")
        return False


def removeDir(path=None):
    """Remove an empty directory. Usage: rmdir <directory>"""
    try:
        if not path or not path[0]:
            print("Error: directory path is required")
            return False

        os.rmdir(path[0])  # Deliberately removes empty directories only.
        print(f"Directory removed: {path[0]}")
        return True

    except OSError as error:
        print(f"Error: {error}")
        return False


def copyPath(path=None):
    """Copy a file or directory. Usage: cp <source> <destination>"""
    try:
        if not path or len(path) < 2 or not path[0] or not path[1]:
            print("Error: source and destination are required")
            return False

        source, destination = path[0], path[1]

        if os.path.isdir(source):
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)

        print(f"Copied: {source} -> {destination}")
        return True

    except (OSError, shutil.Error) as error:
        print(f"Error: {error}")
        return False


def touchFile(path=None):
    """Create an empty file, or update its modification time. Usage: touch <file>"""
    try:
        if not path or not path[0]:
            print("Error: file path is required")
            return False

        filename = path[0]
        with open(filename, "a", encoding="utf-8"):
            os.utime(filename, None)

        print(f"File ready: {filename}")
        return True

    except OSError as error:
        print(f"Error: {error}")
        return False


def readFile(path=None):
    """Print a text file. Usage: cat <file>"""
    try:
        if not path or not path[0]:
            print("Error: file path is required")
            return False

        with open(path[0], "r", encoding="utf-8") as file:
            print(file.read(), end="")

        return True

    except (OSError, UnicodeError) as error:
        print(f"Error: {error}")
        return False


def findPath(path=None):
    """Find files/directories by name. Usage: find <name> [start_directory]"""
    try:
        if not path or not path[0]:
            print("Error: search name is required")
            return False

        query = path[0].casefold()
        start_dir = path[1] if len(path) > 1 and path[1] else os.getcwd()
        found = False

        for root, dirs, files in os.walk(start_dir):
            for name in dirs + files:
                if query in name.casefold():
                    print(os.path.join(root, name))
                    found = True

        if not found:
            print("No matches found.")

        return True

    except OSError as error:
        print(f"Error: {error}")
        return False


def treeDir(path=None):
    """Display a directory tree. Usage: tree [directory]"""
    try:
        root = path[0] if path and path[0] else os.getcwd()

        if not os.path.isdir(root):
            print(f"Error: not a directory: {root}")
            return False

        print(root)

        def _walk(directory, prefix=""):
            try:
                with os.scandir(directory) as scan:
                    entries = sorted(
                        scan,
                        key=lambda entry: (not entry.is_dir(follow_symlinks=False),
                                           entry.name.casefold())
                    )
            except OSError as error:
                print(f"{prefix}[Cannot access: {error}]")
                return

            for index, entry in enumerate(entries):
                is_last = index == len(entries) - 1
                branch = "`-- " if is_last else "|-- "
                print(prefix + branch + entry.name)

                if entry.is_dir(follow_symlinks=False):
                    extension = "    " if is_last else "|   "
                    _walk(entry.path, prefix + extension)

        _walk(root)
        return True

    except OSError as error:
        print(f"Error: {error}")
        return False


if __name__ == "__main__":
    print("You shouldn't run this code dude :P")
    print("Try to run 'Terminal.py'")
