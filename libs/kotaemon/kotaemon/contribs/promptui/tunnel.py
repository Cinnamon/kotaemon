import atexit
import logging
import os
import platform
import stat
import subprocess
from pathlib import Path

import requests

VERSION = "1.0"

machine = platform.machine()
if machine == "x86_64":
    machine = "amd64"

BINARY_REMOTE_NAME = f"frpc_{platform.system().lower()}_{machine.lower()}"
EXTENSION = ".exe" if os.name == "nt" else ""
BINARY_URL = (
    "some-endpoint.com" f"/kotaemon/tunneling/{VERSION}/{BINARY_REMOTE_NAME}{EXTENSION}"
)

BINARY_FILENAME = f"{BINARY_REMOTE_NAME}_v{VERSION}"
BINARY_FOLDER = Path(__file__).parent
BINARY_PATH = f"{BINARY_FOLDER / BINARY_FILENAME}"


logger = logging.getLogger(__name__)


class Tunnel:
    def __init__(self, appname, username, local_port):
        self.proc = None
        self.url = None
        self.appname = appname
        self.username = username
        self.local_port = local_port

    @staticmethod
    def download_binary():
        if not Path(BINARY_PATH).exists():
            print("First time setting tunneling...")
            resp = requests.get(BINARY_URL)

            if resp.status_code == 404:
                raise OSError(
                    f"Cannot set up a share link as this platform is incompatible. "
                    "Please create a GitHub issue with information about your "
                    f"platform: {platform.uname()}"
                )

            if resp.status_code == 403:
                raise OSError(
                    "You do not have permission to setup the tunneling. Please "
                    "make sure that you are within Cinnamon VPN or within other "
                    "approved IPs. If this is new server, please contact @channel "
                    "at #llm-productization to add your IP address"
                )

            resp.raise_for_status()

            # Save file data to local copy
            with open(BINARY_PATH, "wb") as file:
                file.write(resp.content)
            st = os.stat(BINARY_PATH)
            os.chmod(BINARY_PATH, st.st_mode | stat.S_IEXEC)

    def run(self) -> str:
        """Setting up tunneling"""
        if platform.system().lower() == "windows":
            logger.warning("Tunneling is not fully supported on Windows.")

        self.download_binary()
        self.url = self._start_tunnel(BINARY_PATH)
        return self.url

    def kill(self):
        if self.proc is not None:
            print(f"Killing tunnel 127.0.0.1:{self.local_port} <> {self.url}")
            self.proc.terminate()
            self.proc = None

    def _start_tunnel(self, binary: str) -> str:
        command = [
            binary,
            "http",
            "-l",
            str(self.local_port),
            "-i",
            "127.0.0.1",
            "--uc",
            "--sd",
            str(self.appname),
            "-n",
            str(self.appname + self.username),
            "--server_addr",
            "44.229.38.9:7000",
            "--token",
            "Wz807/DyC;#t;#/",
            "--disable_log_color",
        ]
        self.proc = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        atexit.register(self.kill)
        return f"https://{self.appname}.promptui.dm.cinnamon.is"
