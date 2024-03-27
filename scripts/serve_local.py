import platform
import subprocess
from inspect import currentframe, getframeinfo
from pathlib import Path

from decouple import config

system_name = platform.system()

cur_frame = currentframe()
if cur_frame is None:
    raise ValueError("Cannot get the current frame.")
this_file = getframeinfo(cur_frame).filename
this_dir = Path(this_file).parent


def serve_llamacpp_python(local_model_file: Path, **kwargs):
    def guess_chat_format(local_model_file):
        model_name = local_model_file.stem

        # handle known cases that the server backends handle incorrectly
        # this is highly heuristic, should be expand later
        # server backends usually has logic for this but they could still be wrong
        if "qwen" in model_name:
            return "qwen"

        return None

    # default port
    if "port" not in kwargs:
        kwargs["port"] = 31415

    chat_format = guess_chat_format(local_model_file)
    if chat_format:
        kwargs = {**kwargs, "chat_format": chat_format}

    # these scripts create a separate conda env and run the server
    if system_name == "Windows":
        script_file = this_dir / "server_llamacpp_windows.bat"
    elif system_name == "Linux":
        script_file = this_dir / "server_llamacpp_linux.sh"
    elif system_name == "Darwin":
        script_file = this_dir / "server_llamacpp_macos.sh"
    else:
        raise ValueError(f"Unsupported system: {system_name}")

    args = " ".join(f"--{k} {v}" for k, v in kwargs.items())

    cmd = f"{script_file} --model {local_model_file} {args}"
    subprocess.Popen(cmd, shell=True)


def main():
    local_model_file = config("LOCAL_MODEL", default="")

    if not local_model_file:
        print("LOCAL_MODEL not set in the `.env` file.")
        return

    local_model_file = Path(local_model_file)
    if not local_model_file.exists():
        print(f"Local model not found: {local_model_file}")
        return

    print(f"Local model found: {local_model_file}")
    will_start_server = input("Do you want to use this local model ? (y/n): ")

    if will_start_server.lower().strip() not in ["y", "yes"]:
        return

    print("Starting the local server...")
    if local_model_file.suffix == ".gguf":
        serve_llamacpp_python(local_model_file)
    else:
        raise ValueError(f"Unsupported model file type: {local_model_file.suffix}")


if __name__ == "__main__":
    main()
