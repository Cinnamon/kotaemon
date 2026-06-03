# Contributing to Kotaemon

Welcome 👋 to the Kotaemon project! We're thrilled that you're interested in contributing. Whether you're fixing bugs, adding new features, or improving documentation, your efforts are highly appreciated. This guide aims to help you get started with contributing to Kotaemon.

<a href="https://github.com/Cinnamon/kotaemon/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Cinnamon/kotaemon" />
</a>

### Table of Contents

1. [📖 Code of Conduct](#code-of-conduct)
2. [🔁 Contributing via Pull Requests](#contributing-via-pull-requests)
3. [📥 Opening an Issue](#-opening-an-issue)
4. [📝 Commit Messages](#-commit-messages)
5. [🧾 License](#-license)

## 📖 Code of Conduct

Please review our [code of conduct](./CODE_OF_CONDUCT.md), which is in effect at all times. We expect everyone who contributes to this project to honor it.

## 🔁 Contributing via Pull Requests

1. [**Fork the repository**](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo): Click on the [Fork](https://github.com/Cinnamon/kotaemon/fork) button on the repository's page to create a copy of Kotaemon under your GitHub account.

2. [**Clone your code**](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository): Clone your forked repository to your local machine.

3. [**Create new branch**](https://docs.github.com/en/desktop/making-changes-in-a-branch/managing-branches-in-github-desktop): Create a new branch in your forked repo with a descriptive name that reflects your changes.

```sh
git checkout -b descriptive-name-for-your-changes
```

4. **Setup the development environment**: If you are working on the code, make sure to install the necessary dependencies for development

```sh
pip install -e "libs/kotaemon[dev]"
```

5. **Make your changes**: Ensure your code follows the project's coding style and passes all test cases.

   - Check the coding style

   ```sh
   pre-commit run --all-files
   ```

   - Run the tests

   ```sh
   pytest libs/kotaemon/tests/
   ```

6. [**Commit your changes**](https://docs.github.com/en/desktop/making-changes-in-a-branch/committing-and-reviewing-changes-to-your-project-in-github-desktop): Once you are done with your changes, add and commit them with clear messages.

```sh
git add your_changes.py
git commit -m "clear message described your changes."
git push -u origin descriptive-name-for-your-changes
```

7. [**Create a pull request**](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request): When you are satisfied with your changes, [submit a pull request](https://github.com/Cinnamon/kotaemon/compare) from your forked repository to Kotaemon repository. In the pull request, provide a clear description of your changes and any related issues. For the title of the pull request, please refer to our [commit messages convention](#-commit-messages).

8. **Wait for reviews**: Wait for the maintainers to review your pull request. If everything is okay, your changes will be merged into the Kotaemon project.

### GitHub Actions CI Tests

All pull requests must pass the [GitHub Actions Continuous Integration (CI)](https://docs.github.com/en/actions/about-github-actions/about-continuous-integration-with-github-actions) tests before they can be merged. These tests include coding-style checks, PR title validation, unit tests, etc. to ensure that your changes meet the project's quality standards. Please review and fix any CI failures that arise.

## 📥 Opening an Issue

Before [creating an issues](https://github.com/Cinnamon/kotaemon/issues/new/choose), search through existing issues to ensure you are not opening a duplicate. If you are reporting a bug or issue, please provide a reproducible example to help us quickly identify the problem.

## 📝 Commit Messages

### Overview

We use [Angular convention](https://www.conventionalcommits.org/en/) for commit messages to maintain consistency and clarity in our project history. Please take a moment to familiarize yourself with this convention before making your first commit.

_For the sake of simplicity, we use [squashing merge](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/incorporating-changes-from-a-pull-request/about-pull-request-merges#squash-and-merge-your-commits) with pull requests. Therefore, if you contribute via a pull request, just make sure your PR's title, instead of the whole commits, follows this convention._

Commit format:

```sh
<gitmoji> <type>(<scope>): <subject>
<BLANK LINE>
<body>
<BLANK LINE>
<footer>
```

Examples:

```sh
docs(api): update api doc
```

### Commit types

| Types      | Description                                                   |
| :--------- | :------------------------------------------------------------ |
| `feat`     | New features                                                  |
| `fix`      | Bug fix                                                       |
| `docs`     | Documentation only changes                                    |
| `build`    | Changes that affect the build system or external dependencies |
| `chore`    | Something that doesn’t fit the other types                    |
| `ci`       | Changes to our CI configuration files and scripts             |
| `perf`     | Improve performance                                           |
| `refactor` | Refactor code                                                 |
| `revert`   | Revert a previous commit                                      |
| `style`    | Improve structure/format of the code                          |
| `test`     | Add, update or pass tests                                     |

## 🧾 License

All contributions will be licensed under the project's license: [Apache License 2.0](https://github.com/Cinnamon/kotaemon/blob/main/LICENSE.txt).
