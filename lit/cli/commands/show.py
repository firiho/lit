"""Show command - display commit details with diff."""

import click
from datetime import datetime
from lit.core.repository import Repository
from lit.core.objects import Commit
from lit.cli.output import success, error, info, warning
from colorama import Fore, Style


def format_timestamp(timestamp):
    """Format Unix timestamp to readable date."""
    try:
        dt = datetime.fromtimestamp(int(timestamp))
        return dt.strftime("%a %b %d %H:%M:%S %Y %z")
    except:
        return "Unknown date"


@click.command('show')
@click.option('--no-color', is_flag=True, help='Disable colored output')
@click.option('--stat', is_flag=True, help='Show diffstat (summary of changes)')
@click.argument('commit', required=False, default='HEAD')
def show_cmd(no_color, stat, commit):
    """
    Show commit details with diff.
    
    Displays commit metadata (author, date, message) followed by
    the complete diff of changes introduced by that commit.
    
    This is different from 'lit log' which only shows commit metadata
    without the actual changes. 'lit show' gives you the full picture
    of what a commit did.
    
    Examples:
        lit show                # Show HEAD commit with diff
        lit show HEAD           # Same as above
        lit show abc123         # Show specific commit with diff
        lit show main           # Show latest commit on main branch
        lit show --stat         # Show with change summary
    """
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        raise click.Abort()
    
    use_color = not no_color
    
    try:
        # Resolve commit reference
        refs_mgr = repo.refs
        commit_hash = refs_mgr.resolve_reference(commit)
        
        if not commit_hash:
            click.echo(error(f"Not a valid reference: {commit}"))
            raise click.Abort()
        
        # Read commit object
        commit_obj = repo.read_object(commit_hash)
        if not isinstance(commit_obj, Commit):
            click.echo(error(f"Not a valid commit: {commit}"))
            raise click.Abort()
        
        # Display commit header
        if use_color:
            click.echo(f"{Fore.YELLOW}commit {commit_hash}{Style.RESET_ALL}")
        else:
            click.echo(f"commit {commit_hash}")
        
        # Show merge info
        if len(commit_obj.parents) > 1:
            merge_line = "Merge: " + " ".join(p[:7] for p in commit_obj.parents)
            if use_color:
                click.echo(f"{Fore.CYAN}{merge_line}{Style.RESET_ALL}")
            else:
                click.echo(merge_line)
        
        # Author and date
        click.echo(f"Author: {commit_obj.author}")
        date_str = format_timestamp(commit_obj.author_time)
        click.echo(f"Date:   {date_str}")
        
        # Commit message
        click.echo()
        for line in commit_obj.message.split('\n'):
            click.echo(f"    {line}")
        click.echo()
        
        # Get diff
        diff_engine = repo.diff
        
        # Get parent commit (or None for initial commit)
        parent_hash = commit_obj.parents[0] if commit_obj.parents else None
        
        # Compute diff
        diffs = diff_engine.diff_commits(parent_hash, commit_hash)
        
        if not diffs:
            click.echo(info("(no changes)"))
            return
        
        if stat:
            # Show diffstat
            total_additions = 0
            total_deletions = 0
            
            click.echo("Files changed:")
            for diff in diffs:
                additions = sum(1 for hunk in diff.hunks for line in hunk.lines if line.startswith('+'))
                deletions = sum(1 for hunk in diff.hunks for line in hunk.lines if line.startswith('-'))
                total_additions += additions
                total_deletions += deletions
                
                status = "new" if diff.is_new else "deleted" if diff.is_deleted else "modified"
                
                if use_color:
                    changes = f"{Fore.GREEN}+{additions}{Style.RESET_ALL} {Fore.RED}-{deletions}{Style.RESET_ALL}"
                else:
                    changes = f"+{additions} -{deletions}"
                
                click.echo(f"  {diff.path:<40} {status:<10} {changes}")
            
            click.echo()
            if use_color:
                summary = f"{len(diffs)} file(s) changed, {Fore.GREEN}{total_additions} insertions(+){Style.RESET_ALL}, {Fore.RED}{total_deletions} deletions(-){Style.RESET_ALL}"
            else:
                summary = f"{len(diffs)} file(s) changed, {total_additions} insertions(+), {total_deletions} deletions(-)"
            click.echo(summary)
        else:
            # Show full diff
            output = diff_engine.format_diff(diffs, color=use_color)
            click.echo(output)
        
    except click.Abort:
        raise
    except Exception as e:
        click.echo(error(f"Show failed: {e}"))
        import traceback
        traceback.print_exc()
        raise click.Abort()
