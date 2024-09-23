# Getting Started with Kotaemon

![type:video](https://github.com/Cinnamon/kotaemon/assets/25688648/815ecf68-3a02-4914-a0dd-3f8ec7e75cd9)

This page is intended for **end users** who want to use the `kotaemon` tool for Question
Answering on local documents. If you are a **developer** who wants contribute to the project, please visit the [development](development/index.md) page.

## Installation (Online HuggingFace Space)

<details>

<summary>View instruction</summary>

1. Go to [kotaemon_template](https://huggingface.co/spaces/cin-model/kotaemon_template)

2. Use Duplicate function to create your own space

![Duplicate space](https://raw.githubusercontent.com/Cinnamon/kotaemon/main/docs/images/duplicate_space.png)

![Change space params](https://raw.githubusercontent.com/Cinnamon/kotaemon/main/docs/images/change_space_params.png)

3. Wait for the build to complete and start up (apprx 10 mins).

![Wait space build](https://raw.githubusercontent.com/Cinnamon/kotaemon/main/docs/images/space_build.png)

![Close space build](https://raw.githubusercontent.com/Cinnamon/kotaemon/main/docs/images/close_logs_space.png)

4. Follow the first setup instructions (and register for Cohere API key if needed)

![Cohere API](https://raw.githubusercontent.com/Cinnamon/kotaemon/main/docs/images/cohere_api_key.png)

5. Complete the setup and use your own private space!

![App Startup](https://raw.githubusercontent.com/Cinnamon/kotaemon/main/docs/images/initial_startup.png)

</details>

## Installation (Offline)

### Download

Download the `kotaemon-app.zip` file from the [latest release](https://github.com/Cinnamon/kotaemon/releases/latest/).

### Run setup script

0. Unzip the downloaded file.
1. Navigate to the `scripts` folder and start an installer that matches your OS:
   - Windows: `run_windows.bat`. Just double click the file.
   - macOS: `run_macos.sh`
     1. Right click on your file and select Open with and Other.
     2. Enable All Applications and choose Terminal.
     3. NOTE: If you always want to open that file with Terminal, then check Always Open With.
     4. From now on, double click on your file and it should work.
   - Linux: `run_linux.sh`. Please run the script using `bash run_linux.sh` in your terminal.
2. After the installation, the installer will ask to launch the ktem's UI, answer to continue.
3. If launched, the application will be open automatically in your browser.

## Launch

To launch the app after initial setup or any change, simply run the `run_*` script again.

A browser window will be opened and greets you with this screen:

![Chat tab](https://raw.githubusercontent.com/Cinnamon/kotaemon/main/docs/images/chat-tab.png)

## Usage

For how to use the application, see [Usage](usage.md). This page will also be available to
you within the application.

## Feedback

Feel free to create a bug report or a feature request on our [repo](https://github.com/Cinnamon/kotaemon/issues).
