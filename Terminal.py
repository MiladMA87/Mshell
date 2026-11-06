import shlex

import UI
from Dispatcher import run_argv

if __name__ == "__main__":
    UI.reDrawTerminal()
    print()

    while True:
        try:
            command = shlex.split(input(">--> "))
        except (EOFError, KeyboardInterrupt):
            print("\ngoodbye bro...")
            break
        except ValueError:
            print("Error: invalid syntax (unclosed quote?)")
            continue

        if not command:
            continue

        if command[0].lower() == "exit":
            print("goodbye bro...")
            break

        try:
            run_argv(command)
        except KeyboardInterrupt:
            print("\nInterrupted.")
        except Exception as error:
            # A bug inside one command must not kill the whole terminal.
            print(f"Unexpected error: {error}")

        print()
