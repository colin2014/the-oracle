"""CLI commands for maintenance tasks."""

import click
from app import app, db


@click.group()
def cli():
    """Maintenance CLI commands."""
    pass


@cli.command()
@click.option('--hours', default=3, help='Hours to consider expired (default: 3)')
def cleanup_tests(hours):
    """Clean up expired test submissions.

    This command:
    - Auto-submits live tests (in_progress) older than N hours
    - Deletes unstarted tests with no answers older than N hours
    """
    with app.app_context():
        from test_cleanup import cleanup_expired_tests
        result = cleanup_expired_tests(hours=hours)

        click.echo("\n✓ Test Cleanup Completed\n")
        click.echo(f"  Auto-submitted (saved): {result['auto_submitted']}")
        click.echo(f"  Deleted (unstarted):    {result['deleted_unstarted']}")
        click.echo(f"  Total cleaned:          {result['total_cleaned']}")
        click.echo(f"  Cutoff time:            {result['cutoff_time']}\n")


@cli.command()
def cleanup_games():
    """Clean up expired game sessions.

    This command removes:
    - Finished games older than 7 days
    - Abandoned games (created but never started)
    """
    with app.app_context():
        from models import GameSession
        from datetime import datetime, timedelta

        cutoff = datetime.utcnow() - timedelta(days=7)

        # Delete finished games older than 7 days
        deleted_finished = GameSession.query.filter(
            GameSession.status == "finished",
            GameSession.finished_at < cutoff
        ).delete()

        # Delete abandoned games (created over 24 hours ago, never started)
        abandoned_cutoff = datetime.utcnow() - timedelta(hours=24)
        deleted_abandoned = GameSession.query.filter(
            GameSession.status == "lobby",
            GameSession.created_at < abandoned_cutoff
        ).delete()

        db.session.commit()

        click.echo("\n✓ Game Cleanup Completed\n")
        click.echo(f"  Deleted finished games: {deleted_finished}")
        click.echo(f"  Deleted abandoned:      {deleted_abandoned}")
        click.echo(f"  Total deleted:          {deleted_finished + deleted_abandoned}\n")


if __name__ == '__main__':
    cli()
