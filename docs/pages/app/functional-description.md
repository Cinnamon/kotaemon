## User group / tenant management

### Create new user group

(6 man-days)

**Description**: each client has a dedicated user group. Each user group has an
admin user who can do administrative tasks (e.g. creating user account in that
user group...). The workflow for creating new user group is as follow:

1. Cinnamon accesses the user group management UI.
2. On "Create user group" panel, we supply:
   a. Client name: e.g. Apple.
   b. Sub-domain name: e.g. apple.
   c. Admin email, username & password.
3. The system will:
   a. An Aurora Platform deployment with the specified sub-domain.
   b. Send an email to the admin, with the username & password.

**Expectation**:

- The admin can go to the deployed Aurora Platform.
- The admin can login with the specified username & password.

**Condition**:

- When sub-domain name already exists, raise error.
- If error sending email to the client, raise the error, and delete the
  newly-created user-group.
- Password rule:
  - Have at least 8 characters.
  - Must contain uppercase, lowercase, number and symbols.

---

### Delete user group

(2 man-days)

**Description**: in the tenant management page, we can delete the selected user
group. The user flow is as follow:

1. Cinnamon accesses the user group management UI,
2. View list of user groups.
3. Next to target user group, click delete.
4. Confirm whether to delete.
5. If Yes, delete the user group. If No, cancel the operation.

**Expectation**: when a user group is deleted, we expect to delete everything
related to the user groups: domain, files, databases, caches, deployments.

## User management

---

### Create user account (for admin user)

(1 man-day)

**Description**: the admin user in the client's account can create user account
for that user group. To create the new user, the client admin do:

1. Navigate to "Admin" > "Users"
2. In the "Create user" panel, supply:
   - Username
   - Password
   - Confirm password
3. Click "Create"

**Expectation**:

- The user can create the account.
- The username:
  - Is case-insensitive (e.g. Moon and moon will be the same)
  - Can only contains these characters: a-z A-Z 0-9 \_ + - .
  - Has maximum length of 32 characters
- The password is subjected to the following rule:
  - 8-character minimum length
  - Contains at least 1 number
  - Contains at least 1 lowercase letter
  - Contains at least 1 uppercase letter
  - Contains at least 1 special character from the following set, or a
    non-leading, non-trailing space character: `^ $ * . [ ] { } ( ) ? - " ! @ # % & / \ , > < ' : ; | _ ~ ` + =

---

### Delete user account (for admin user)

**Description**: the admin user in the client's account can delete user account.
Once an user account is deleted, he/she cannot login to Aurora Platform.

1. The admin user navigates to "Admin" > "Users".
2. In the user list panel, next to the username, the admin click on the "Delete"
   button. The Confirmation dialog appears.
3. If "Delete", the user account is deleted. If "Cancel", do nothing. The
   Confirmation dialog disappears.

**Expectation**:

- Once the user is deleted, the following information relating to the user will
  be deleted:
  - His/her personal setting.
  - His/her conversations.
- The following information relating to the user will still be retained:
  - His/her uploaded files.

---

### Edit user account (for admin user)

**Description**: the admin user can change any information about the user
account, including password. To change user information:

1. The admin user navigates to "Admin" > "Users".
2. In the user list panel, next to the username, the admin click on the "Edit"
   button.
3. The user list disappears, the user detail appears, with the following
   information show up:
   - Username: (prefilled the username)
   - Password: (blank)
   - Confirm password: (blank)
4. The admin can edit any of the information, and click "Save" or "Cancel".
   - If "Save": the information will be updated to the database, or show
     error per Expectation below.
   - If "Cancel": skip.
5. If Save success or Cancel, transfer back to the user list UI, where the user
   information is updated accordingly.

**Expectation**:

- If the "Password" & "Confirm password" are different from each other, show
  error: "Password mismatch".
- If both "Password" & \*"Confirm password" are blank, don't change the user
  password.
- If changing password, the password rule is subjected to the same rule when
  creating user.
- It's possible to change username. If changing username, the target user has to
  use the new username.

---

### Sign-in

(3 man-days)

**Description**: the users can sign-in to Aurora Platform as follow:

1. User navigates to the URL.
2. If the user is not logged in, the UI just shows the login screen.
3. User types username & password.
4. If correct, the user will proceed to normal working UI.
5. If incorrect, the login screen shows text error.

---

### Sign-out

(1 man-day)

**Description**: the user can sign-out of Aurora Platform as follow:

1. User navigates to the Settings > User page.
2. User click on logout.
3. The user is signed out to the UI login screen.

**Expectation**: the user is completely signed out. Next time he/she uses the
Aurora Platform, he/she has to login again.

---

### Change password

**Description**: the user can change their password as follow:

1. User navigates to the Settings > User page.
2. In the change password section, the user provides these info and click
   Change:
   - Current password
   - New password
   - Confirm new password
3. If changing successfully, then the password is changed. Otherwise, show the
   error on the UI.

**Expectation**:

- If changing password succeeds, next time they logout/login to the system, they
  can use the new password.
- Password rule (Same as normal password rule when creating user)
- Errors:
  - Password does not match.
  - Violated password rules.

---

## Chat

### Chat to the bot

**Description**: the Aurora Platform focuses on question and answering over the
uploaded data. Each chat has the following components:

- Chat message: show the exchange between bots and humans.
- Text input + send button: for the user to input the message.
- Data source panel: for selecting the files that will scope the context for the
  bot.
- Information panel: showing evidence as the bot answers user's questions.

The chat workflow looks as follow:

1. [Optional] User select files that they want to scope the context for the bot.
   If the user doesn't select any files, then all files on Aurora Platform will
   be the context for the bot.
   - The user can type multi-line messages, using "Shift + Enter" for
     line-break.
2. User sends the message (either clicking the Send button or hitting the Enter
   key).
3. The bot in the chat conversation will return "Thinking..." while it
   processes.
4. The information panel on the right begin to show data related to the user
   message.
5. The bot begins to generate answer. The "Thinking..." placeholder disappears..

**Expecatation**:

- Messages:
  - User can send multi-line messages, using "Shift + Enter" for line-break.
  - User can thumbs up, thumbs down the AI response. This information is
    recorded in the database.
  - User can click on a copy button on the chat message to copy the content to
    clipboard.
- Information panel:
  - The information panel shows the latest evidence.
  - The user can click on the message, and the reference for that message will
    show up on the "Reference panel" (feature in-planning).
  - The user can click on the title to show/hide the content.
  - The whole information panel can be collapsed.
- Chatbot quality:
  - The user can converse with the bot. The bot answer the user's requests in a
    natural manner.
  - The bot message should be streamed to the UI. The bot don't wait to gather
    alll the text response, then dump all of them at once.

### Conversation - switch

**Description**: users can jump around between different conversations. They can
see the list of all conversations, can select an old converation, and continue
the chat under the context of the old conversation. The switching workflow is
like this:

1. Users click on the conversation dropdown. It will show a list of
   conversations.
2. Within that dropdown, the user selects one conversation.
3. The chat messages, information panel, and selected data will show the content
   in that old chat.
4. The user can continue chatting as normal under the context of this old chat.

**Expectation**:

- In the conversation drop down list, the conversations are ordered in created
  date order.
- When there is no conversation, the conversation list is empty.
- When there is no conversation, the user can still converse with the chat bot.
  When doing so, it automatically create new conversation.

### Conversation - create

**Description**: the user can explicitly start a new conversation with the
chatbot:

1. User click on the "New" button.
2. The new conversation is automatically created.

**Expectation**:

- The default conversation name is the current datetime.
- It become selected.
- It is added to the conversation list.

### Conversation - rename

**Description**: user can rename the chatbot by typing the name, and click on
the Rename button next to it.

- If rename succeeds: the name shown in the 1st dropdown will change accordingly
- If rename doesn't succeed: show error message in red color below the rename section

**Condition**:

- Name constraint:
  - Min characters: 1
  - Max characters: 40
  - Could not having the same name with an existing conversation of the same
    user.

### Conversation - delete

**Description**: user can delete the existing conversation as follow:

1. Click on Delete button.
2. The UI show confirmation with 2 buttons:
   - Delete
   - Cancel.
3. If Delete, delete the conversation, switch to the next oldest conversation,
   close the confirmation panel.
4. If cancel, just close the confirmation panel.

## File management

The file management allows users to upload, list and delete files that they
upload to the Aurora Platform

### Upload file

**Description**: the user can upload files to the Aurora Platform. The uploaded
files will be served as context for our chatbot to refer to when it converses
with the user. To upload file, the user:

1. Navigate to the File tab.
2. Within the File tab, there is an Upload section.
3. User can add files to the Upload section through drag & drop, and or by click
   on the file browser.
4. User can select some options relating to uploading and indexing. Depending on
   the project, these options can be different. Nevertheless, they will discuss
   below.
5. User click on "Upload and Index" button.
6. The app show notifications when indexing starts and finishes, and when errors
   happen on the top right corner.

**Options**:

- Force re-index file. When user tries to upload files that already exists on
  the system:
  - If this option is True: will re-index those files.
  - If this option is False: will skip indexing those files.

**Condition**:

- Max number of files: 100 files.
- Max number of pages per file: 500 pages
- Max file size: 10 MB

### List all files

**Description**: the user can know which files are on the system by:

1. Navigate to the File tab.
2. By default, it will show all the uploaded files, each with the following
   information: file name, file size, number of pages, uploaded date
3. The UI also shows total number of pages, and total number of sizes in MB.

### Delete file

**Description**: users can delete files from this UI to free up the space, or to
remove outdated information. To remove the files:

1. User navigate to the File tab.
2. In the list of file, next to each file, there is a Delete button.
3. The user clicks on the Delete button. Confirmation dialog appear.
4. If Delete, delete the file. If Cancel, close the confirmation dialog.

**Expectation**: once the file is deleted:

- The database entry of that file is deleted.
- The file is removed from "Chat - Data source".
- The total number of pages and MB sizes are reduced accordingly.
- The reference to the file in the information panel is still retained.
