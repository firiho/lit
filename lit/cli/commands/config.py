"""Config command - manage repository configuration."""

import click
from pathlib import Path
from lit.core.repository import Repository
from lit.cli.output import success, error, info
import configparser


@click.group('config')
def config_cmd():
    """Get and set repository or global options."""
    pass


@config_cmd.command('set')
@click.argument('key')
@click.argument('value')
@click.option('--global', 'is_global', is_flag=True, help='Set global config')
def config_set(key, value, is_global):
    """
    Set a config value.
    
    Examples:
        lit config set user.name "Your Name"
        lit config set user.email "your@email.com"
        lit config set --global user.name "Your Name"
    """
    if not is_global:
        repo = Repository.find_repository()
        if not repo:
            click.echo(error("Not a lit repository (use --global for global config)"))
            raise click.Abort()
        config_file = repo.config_file
    else:
        config_file = Path.home() / '.litconfig'
    
    config = configparser.ConfigParser()
    if config_file.exists():
        config.read(config_file)
    
    section, option = key.split('.', 1) if '.' in key else ('core', key)
    
    if not config.has_section(section):
        config.add_section(section)
    
    config.set(section, option, value)
    
    with open(config_file, 'w') as f:
        config.write(f)
    
    scope = "global" if is_global else "repository"
    click.echo(success(f"Set {scope} config: {key} = {value}"))


@config_cmd.command('get')
@click.argument('key')
@click.option('--global', 'is_global', is_flag=True, help='Get global config only')
def config_get(key, is_global):
    """
    Get a config value.
    
    Examples:
        lit config get user.name
        lit config get user.email
    """
    config = configparser.ConfigParser()
    
    if not is_global:
        repo = Repository.find_repository()
        if repo and repo.config_file.exists():
            config.read(repo.config_file)
    
    global_config = Path.home() / '.litconfig'
    if global_config.exists():
        config.read(global_config)
    
    section, option = key.split('.', 1) if '.' in key else ('core', key)
    
    try:
        value = config.get(section, option)
        click.echo(value)
    except (configparser.NoSectionError, configparser.NoOptionError):
        click.echo(error(f"Config key not found: {key}"))
        raise click.Abort()


@config_cmd.command('list')
@click.option('--global', 'is_global', is_flag=True, help='List global config only')
def config_list(is_global):
    """
    List all config values.
    
    Examples:
        lit config list
        lit config list --global
    """
    config = configparser.ConfigParser()
    
    if not is_global:
        repo = Repository.find_repository()
        if repo and repo.config_file.exists():
            config.read(repo.config_file)
            click.echo(info("Repository config:"))
            for section in config.sections():
                for key, value in config.items(section):
                    click.echo(f"  {section}.{key}={value}")
            click.echo()
    
    global_config = Path.home() / '.litconfig'
    if global_config.exists():
        global_cfg = configparser.ConfigParser()
        global_cfg.read(global_config)
        click.echo(info("Global config:"))
        for section in global_cfg.sections():
            for key, value in global_cfg.items(section):
                click.echo(f"  {section}.{key}={value}")
    
    if not config.sections() and not global_config.exists():
        click.echo(info("No configuration set"))
