"""Main CLI entry point for Lit."""

import click
from colorama import init

from lit.cli.output import BANNER, success, info, warning, error
from lit.cli.commands import (init_cmd, add_cmd, commit_cmd, config_cmd, 
                              status_cmd, log_cmd, branch_cmd, checkout_cmd, switch_cmd,
                              show_ref_cmd, symbolic_ref_cmd, diff_cmd, show_cmd, merge_cmd,
                              clone_cmd, pull_cmd, push_cmd, remote_cmd)

# Initialize colorama for cross-platform colored output
init(autoreset=True)


class LitGroup(click.Group):
    """Custom Group class to display banner before help."""
    
    def format_help(self, ctx, formatter):
        """Override to add banner before help text."""
        click.echo(BANNER)
        super().format_help(ctx, formatter)


@click.group(cls=LitGroup)
@click.version_option(version='0.1.0')
def cli():
    pass


# Register commands
cli.add_command(clone_cmd)
cli.add_command(init_cmd)
cli.add_command(add_cmd)
cli.add_command(commit_cmd)
cli.add_command(config_cmd)
cli.add_command(status_cmd)
cli.add_command(log_cmd)
cli.add_command(branch_cmd)
cli.add_command(checkout_cmd)
cli.add_command(switch_cmd)
cli.add_command(show_ref_cmd)
cli.add_command(symbolic_ref_cmd)
cli.add_command(diff_cmd)
cli.add_command(show_cmd)
cli.add_command(merge_cmd)
cli.add_command(remote_cmd)
cli.add_command(pull_cmd)
cli.add_command(push_cmd)

def main():
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main()
