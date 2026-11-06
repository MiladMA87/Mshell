import platform
import subprocess
import webbrowser
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen


# Every command receives its arguments as a list (without the command name).
# With no arguments the list is empty: []


def _get_host(path):
    """Return the first non-empty argument, or None."""
    if path and path[0]:
        return path[0].strip()
    return None


def _run_network_command(command, timeout=60):
    """Run a network diagnostic command without invoking a shell."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout
        )

        output = result.stdout.strip()
        error_output = result.stderr.strip()

        if output:
            print(output)
        if error_output:
            print(error_output)

        if result.returncode == 0:
            return True

        print(f"Command exited with code {result.returncode}")
        return False

    except FileNotFoundError:
        print(f"Error: command not found: {command[0]}")
        return False
    except subprocess.TimeoutExpired:
        print("Error: command timed out")
        return False
    except OSError as error:
        print(f"Error: {error}")
        return False


def ping(path=None):
    """Ping a host (4 packets). Usage: ping [host]  (default: google.com)"""
    host = _get_host(path) or "google.com"
    count_arg = "-n" if platform.system() == "Windows" else "-c"
    return _run_network_command(["ping", count_arg, "4", host], timeout=30)


def openWeb(path=None):
    """Open a website in the browser. Usage: web <url>"""
    try:
        url = _get_host(path)
        if not url:
            print("Error: URL is required")
            return False

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        webbrowser.open_new_tab(url)
        return True

    except Exception as error:
        print(f"Error: {error}")
        return False


def ipconfig(path=None):
    """Show network interface configuration. Usage: ipconfig"""
    system = platform.system()
    if system == "Windows":
        command = ["ipconfig", "/all"]
    elif system == "Darwin":
        command = ["ifconfig"]
    else:
        command = ["ip", "addr"]

    return _run_network_command(command)


def tracert(path=None):
    """Trace the route to a host. Usage: tracert <host>"""
    host = _get_host(path)
    if not host:
        print("Error: host is required")
        return False

    if platform.system() == "Windows":
        command = ["tracert", "-h", "15", host]
    else:
        command = ["traceroute", "-m", "15", host]

    return _run_network_command(command, timeout=90)


def nslookup(path=None):
    """Look up DNS records for a host. Usage: nslookup <host>"""
    host = _get_host(path)
    if not host:
        print("Error: host is required")
        return False

    return _run_network_command(["nslookup", host], timeout=30)


def netstat(path=None):
    """Show network connections and listening ports. Usage: netstat"""
    command = ["netstat", "-ano"] if platform.system() == "Windows" else ["netstat", "-an"]
    return _run_network_command(command, timeout=30)


def hostname(path=None):
    """Print this computer's network name. Usage: hostname"""
    print(platform.node())
    return True


def download(path=None):
    """Download a URL. Usage: download <url> [output_file]"""
    try:
        url = _get_host(path)
        if not url:
            print("Error: URL is required")
            return False

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        parsed = urlparse(url)
        if not parsed.hostname:
            print("Error: invalid URL")
            return False

        if len(path) > 1 and path[1]:
            destination = Path(path[1])
        else:
            destination = Path(Path(unquote(parsed.path)).name or "download.bin")

        request = Request(url, headers={"User-Agent": "MiladMA87-Shell/0.1"})

        with urlopen(request, timeout=30) as response:
            with destination.open("wb") as file:
                while True:
                    chunk = response.read(1024 * 64)
                    if not chunk:
                        break
                    file.write(chunk)

        print(f"Downloaded: {url}")
        print(f"Saved to: {destination}")
        return True

    except (OSError, ValueError) as error:
        print(f"Download error: {error}")
        return False


if __name__ == "__main__":
    print("You shouldn't run this code dude :P")
    print("Try to run 'Terminal.py'")
