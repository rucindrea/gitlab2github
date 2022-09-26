import functools
import operator
import json
import time
import re
import os

import click
from loguru import logger
from github import Github
from gitlab import Gitlab


uploads_pattern = re.compile("(/uploads/[^\s\)]+)")


def slow_down(_func=None, *, rate=1):
    """Sleep a given amount of seconds before calling the function."""

    def decorator_slow_down(func):
        @functools.wraps(func)
        def wrapper_slow_down(*args, **kwargs):
            time.sleep(rate)
            return func(*args, **kwargs)
        return wrapper_slow_down

    if _func is None:
        return decorator_slow_down
    else:
        return decorator_slow_down(_func)


def retry(_func=None, *, times=1, delay=0, forever=False):
    """Retry the function a given amount of times."""

    def decorator_retry(func):
        @functools.wraps(func)
        def wrapper_retry(*args, **kwargs):
            attempt = 1
            timeout = delay

            while forever or attempt < times:
                try:
                    logger.info("Attempt #{} for {!r}.", attempt, func)
                    return func(*args, **kwargs)
                except Exception as error:
                    logger.error("An error ocurred on attempt #{}.", attempt)
                    logger.error(error)

                    attempt += 1

                    logger.info("Sleep for {} seconds.", timeout)

                    time.sleep(timeout)
                    timeout += 5 * 60

                    if not forever and attempt == times:
                        raise error

        return wrapper_retry

    if _func is None:
        return decorator_retry
    else:
        return decorator_retry(_func)


def fix_upload_links(text, url):
    return uploads_pattern.sub(r'{}\1'.format(url), text)


def fix_mentions(text, users):
    for user in users:
        text = text.replace(
            "@{}".format(user["username"]),
            "[@{}]({})".format(user["username"], user["web_url"])
        )

    return text


def add_issue_footer(description, url):
    message = "<sub>You can find the original issue from GitLab [here]({}).</sub>\n".format(url)

    if description:
        return (
            description
            + "\n"
            + "\n"
            + "---\n"
            + message
        )

    return message


def add_comment_footer(comment, url):
    return (
        comment
        + "\n"
        + "\n"
        + "---\n"
        + "<sub>You can find the comment from GitLab [here]({}).</sub>\n".format(url)
    )


@retry(delay=60 * 20, forever=True)
@slow_down(rate=5)
def create_github_issue(project, title, description=None, labels=None):
    """Crate a GitHub issue."""

    return project.create_issue(
        title=title,
        body=description,
        labels=labels,
    )


@retry(delay=60 * 20, forever=True)
@slow_down(rate=5)
def close_github_issue(issue):
    """Close a GitHub issue."""

    issue.edit(state='closed')


@retry(delay=60 * 20, forever=True)
@slow_down(rate=5)
def create_github_comment(issue, comment):
    """Leave a comment on a github issue."""

    return issue.create_comment(comment)


@retry(delay=60 * 20, forever=True)
@slow_down(rate=5)
def create_github_label(project, name, description=None, color=None):
    """Create a new label."""

    logger.info("Create label '{}'.", name)

    logger.debug("Name: {}", name)
    logger.debug("Description: {}", description)
    logger.debug("Color: {}", color)

    project.create_label(name, color, description=description)


def move_labels(gl_project, gh_project):
    """Move labels from GitLab to GitLab."""

    gl_labels = {gl_label for gl_label in gl_project.labels.list(iterator=True)}
    gh_labels = gh_project.get_labels()

    # excluded_labels = ["Doing", "To Do", "In Code Review", "Testing"]
    excluded_labels = []

    for gl_label in gl_labels:
        if gl_label.name.lower() not in (gh_label.name for gh_label in gh_labels):
            if gl_label.name in excluded_labels:
                continue

            logger.info("Move label '{}'.", gl_label.name)
            click.echo("  * Move label '{}'".format(gl_label.name))

            title = gl_label.name.lower()
            color = gl_label.color.replace("#", "") # GitHub expects the hex color without the "#"
            description = gl_label.description[:100] if gl_label.description else "" # GitHub doesn't allow descriptions longer than 100 characters

            create_github_label(gh_project, title, description=description, color=color)

    if "gitlab" not in (gh_label.name for gh_label in gh_labels):
        create_github_label(
            gh_project, "gitlab",
            description="For issues moved from GitLab",
            color="FC6D27"
        )


def move_comments(gl_project, gl_issue, gh_issue):
    """Move issue comments from GitLab to GitLab."""

    for note in gl_issue.notes.list(iterator=True):
        # Skip private comments
        if note.confidential:
            continue

        if not note.system:
            logger.info("Move comment '{}'.", note.id)
            click.echo("    * Move comment {}".format(note.id))

            comment = fix_upload_links(note.body, gl_project.web_url)
            comment = fix_mentions(comment, gl_issue.participants())
            comment = add_comment_footer(comment, "{}#note_{}".format(gl_issue.web_url, note.id))

            create_github_comment(gh_issue, comment)


def move_issues(gl_project, gh_project):
    """Move issues form GitLab to GitHub."""

    for gl_issue in sorted(gl_project.issues.list(iterator=True), key=operator.attrgetter('iid')):
        # Skip private issues
        if gl_issue.confidential:
            continue

        logger.info("Move issue #{}.", gl_issue.iid)
        click.echo("  * Move issue #{}".format(gl_issue.iid))

        issue_description = gl_issue.description or ""
        issue_description = fix_upload_links(issue_description, gl_project.web_url)
        issue_description = fix_mentions(issue_description, gl_issue.participants())
        issue_description = add_issue_footer(issue_description, gl_issue.web_url)

        gh_issue = None
        gh_issue = create_github_issue(
            gh_project,
            gl_issue.title,
            description=issue_description,
            labels=[*[gl_label.lower() for gl_label in gl_issue.labels], 'gitlab']
        )
        logger.info("New issue #{} created.", gh_issue.number)

        if gl_issue.state == 'closed':
            close_github_issue(gh_issue)

        move_comments(gl_project, gl_issue, gh_issue)


def github2gitlab(gitlab_repo, github_repo, gitlab_access_token, github_access_token):
    """Move labels, issues and comments from GitLab to GitHub."""

    gl = Gitlab(private_token=gitlab_access_token)
    gh = Github(github_access_token)

    gl_project = gl.projects.get(gitlab_repo)
    gh_project = gh.get_repo(github_repo)

    move_labels(gl_project, gh_project)
    move_issues(gl_project, gh_project)
