from Commands import CommandsDict


def get_help():
    for key, guide in CommandsDict.items():
        print(f"\t{key}\t->\t{guide['description']}")
    print("\thelp\t->\tShow this list")
    print("\texit\t->\tClose the terminal")


def run_argv(argv):
    """Run one already-split command line. Used by the terminal AND by the remote receiver."""
    if not argv:
        return True

    key, args = argv[0].lower(), argv[1:]

    if key in CommandsDict:
        CommandsDict[key]["function"](args)
        return True

    if key == "help":
        get_help()
        return True

    print("unknown command...")
    return False


if __name__ == "__main__":
    print("You shouldn't run this code dude :P")
    print("Try to run 'Terminal.py'")
