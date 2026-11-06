import System.Kernel as Kernel
import Internet.Web as Web
import Internet.Remote as Remote
import UI

# To add a new command, add one entry here:
# "name": {"function": some_function, "description": "what it does"}
# The function must accept one parameter: a list of arguments.

CommandsDict = {
    "ls":       {"function": Kernel.listDir,    "description": "List directory contents"},
    "cd":       {"function": Kernel.changeDir,  "description": "Change current directory"},
    "mkdir":    {"function": Kernel.makeDir,    "description": "Create a new directory"},
    "cwd":      {"function": Kernel.getCwd,     "description": "Show current directory path"},
    "clear":    {"function": UI.reDrawTerminal, "description": "Clear the terminal"},
    "mvdir":    {"function": Kernel.moveDir,    "description": "Move a file/folder to a new path"},
    "rename":   {"function": Kernel.reNameDir,  "description": "Rename a file/folder"},
    "rm":       {"function": Kernel.removeFile, "description": "Remove a file"},
    "rmdir":    {"function": Kernel.removeDir,  "description": "Remove an empty directory"},
    "cp":       {"function": Kernel.copyPath,   "description": "Copy files or directories"},
    "touch":    {"function": Kernel.touchFile,  "description": "Create an empty file"},
    "cat":      {"function": Kernel.readFile,   "description": "Read file contents"},
    "find":     {"function": Kernel.findPath,   "description": "Search files and directories"},
    "tree":     {"function": Kernel.treeDir,    "description": "Display directory tree"},
    "ping":     {"function": Web.ping,          "description": "Check network connectivity"},
    "web":      {"function": Web.openWeb,       "description": "Open a website"},
    "ipconfig": {"function": Web.ipconfig,      "description": "Show network configuration"},
    "tracert":  {"function": Web.tracert,       "description": "Trace network route"},
    "nslookup": {"function": Web.nslookup,      "description": "DNS lookup"},
    "netstat":  {"function": Web.netstat,       "description": "Show network connections"},
    "hostname": {"function": Web.hostname,      "description": "Show computer hostname"},
    "download": {"function": Web.download,      "description": "Download a file"},
    "exec":     {"function": Remote.execMode,   "description": "Remote mode: control other PCs on your LAN"},
    "listen":   {"function": Remote.listen,     "description": "Let other PCs on your LAN control this one"},
}


if __name__ == "__main__":
    print("You shouldn't run this code dude :P")
    print("Try to run 'Terminal.py'")
