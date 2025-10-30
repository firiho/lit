"""Main CLI entry point for Lit."""

import click
from colorama import init

from lit.cli.output import BANNER, success, info, warning, error
from lit.cli.commands import init_cmd

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
cli.add_command(init_cmd)


@cli.command()
def placeholder():
    """Testing commands"""
    click.echo(success("Lit - Phase 1 Setup Complete!"))
    click.echo(warning("Core functionality will be implemented in Phase 1 Step 2."))
    click.echo(info("Colorama is working! 🎨"))


def main():
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main()
