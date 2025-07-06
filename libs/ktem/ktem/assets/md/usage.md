# Basic Usage

## 1. Upload your documents

![file index tab](https://raw.githubusercontent.com/Cinnamon/kotaemon/main/docs/images/file-index-tab.png)

In order to do QA on your documents, you need to upload them to the application first.
Navigate to the `File Index` tab and you will see 2 sections:

1. File upload:
   - Drag and drop your file to the UI or select it from your file system.
     Then click `Upload and Index`.
   - The application will take some time to process the file and show a message once it is done.
2. File list:
   - This section shows the list of files that have been uploaded to the application and allows users to delete them.

## 2. Chat with your documents

![chat tab](https://raw.githubusercontent.com/Cinnamon/kotaemon/main/docs/images/chat-tab.png)

Now navigate back to the `Chat` tab. The chat tab is divided into 3 regions:

1. Conversation Settings Panel
   - Here you can select, create, rename, and delete conversations.
     - By default, a new conversation is created automatically if no conversation is selected.
   - Below that you have the file index, where you can choose whether to disable, select all files, or select which files to retrieve references from.
     - If you choose "Disabled", no files will be considered as context during chat.
     - If you choose "Search All", all files will be considered during chat.
     - If you choose "Select", a dropdown will appear for you to select the
       files to be considered during chat. If no files are selected, then no
       files will be considered during chat.
2. Chat Panel
   - This is where you can chat with the chatbot.
3. Information Panel
   - Supporting information such as the retrieved evidence and reference will be
     displayed here.
