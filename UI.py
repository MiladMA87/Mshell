import System.Kernel as Kernel

logo = """
███╗   ███╗██╗██╗      █████╗ ██████╗ ███╗   ███╗ █████╗  █████╗ ███████╗
████╗ ████║██║██║     ██╔══██╗██╔══██╗████╗ ████║██╔══██╗██╔══██╗╚════██║
██╔████╔██║██║██║     ███████║██║  ██║██╔████╔██║███████║╚█████╔╝    ██╔╝
██║╚██╔╝██║██║██║     ██╔══██║██║  ██║██║╚██╔╝██║██╔══██║██╔══██╗   ██╔╝ 
██║ ╚═╝ ██║██║███████╗██║  ██║██████╔╝██║ ╚═╝ ██║██║  ██║╚█████╔╝   ██║  
╚═╝     ╚═╝╚═╝╚══════╝╚═╝  ╚═╝╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝ ╚════╝    ╚═╝ 
"""


def reDrawTerminal(path=None):
    """Clear the screen and print the banner. Usage: clear"""
    Kernel.clear()
    print(logo)
    print("MiladMA87 Shell")
    print("Version: 0.1.0")
    print("\nto get help just write 'help'")


if __name__ == "__main__":
    print("You shouldn't run this code dude :P")
    print("Try to run 'Terminal.py'")
