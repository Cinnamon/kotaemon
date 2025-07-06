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

![information panel](https://raw.githubusercontent.com/Cinnamon/kotaemon/develop/docs/images/info-panel-scores.png)

- Supporting information such as the retrieved evidence and reference will be
  displayed here.
- Direct citation for the answer produced by the LLM is highlighted.
- The confidence score of the answer and relevant scores of evidences are displayed to quickly assess the quality of the answer and retrieved content.

- Meaning of the score displayed:
  - **Answer confidence**: answer confidence level from the LLM model.
  - **Relevance score**: overall relevant score between evidence and user question.
  - **Vectorstore score**: relevant score from vector embedding similarity calculation (show `full-text search` if retrieved from full-text search DB).
  - **LLM relevant score**: relevant score from LLM model (which judge relevancy between question and evidence using specific prompt).
  - **Reranking score**: relevant score from Cohere [reranking model](https://cohere.com/rerank).

Generally, the score quality is `LLM relevant score` > `Reranking score` > `Vectorscore`.
By default, overall relevance score is taken directly from LLM relevant score. Evidences are sorted based on their overall relevance score and whether they have citation or not.
