import timeit

import click

from .gitlab2github import github2gitlab


@click.command()
@click.option('-ghr', '--github-repo', 'github_repo', envvar='GITHUB_REPO', required=True, help='GitHub repository name with namespace.')
@click.option('-glr', '--gitlab-repo', 'gitlab_repo', envvar='GITLAB_REPO', required=True, help='GitLab repository name with namespace.')
@click.option('-ght', '--github-token', 'github_access_token', envvar='GITHUB_TOKEN', required=True, help='GitHub access token.')
@click.option('-glt', '--gitlab-token', 'gitlab_access_token', envvar='GITLAB_TOKEN', required=False, help='GitLab access token.')
def cli(github_repo, gitlab_repo, github_access_token, gitlab_access_token):
    """A simple python script for migrating issues from GitLab to GitHub."""

    click.echo()
    click.secho("  > GitLab Repo: {}".format(gitlab_repo))
    click.secho("  > GitHub Repo: {}".format(github_repo))
    click.secho("  > GitLab Token: {}".format(gitlab_access_token))
    click.secho("  > GitHub Token: {}".format(github_access_token))
    click.echo()

    click.echo("Moving issues from '{}' to '{}'...".format(gitlab_repo, github_repo))
    click.echo()

    click.confirm("Do you want to continue?", abort=True)
    click.echo()

    start = timeit.default_timer()
    github2gitlab(gitlab_repo, github_repo, gitlab_access_token, github_access_token)
    elapsed = timeit.default_timer() - start

    click.echo()
    click.echo("Execution time: {} seconds".format(elapsed))

    click.echo()
    click.echo("Done.")
    click.echo()


if __name__ == "__main__":
    cli()
