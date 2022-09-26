# gitlab2github

A simple python script for migrating issues from GitLab to GitHub.

## Setup

```
$ pip install -r requirements.txt
```

## Usage

To move all issues from a GitLab repository to GitHub run the following commands:

```
$ export GITLAB_TOKEN=xxxxxxxxx
$ export GITHUB_TOKEN=xxxxxxxxx
$ export GITLAB_REPO=namespace/name
$ export GITHUB_REPO=namespace/name
$ python -m gitlab2github
```

Getting help on arguments or option names:

```
$ python -m gitlab2github --help
```

## License

This project is licensed under the [MIT License](LICENSE).
