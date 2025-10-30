"""CLI output utilities and formatting."""

from colorama import Fore, Style

# ASCII art banner for Lit CLI
BANNER = f"""
{Fore.YELLOW}╔════════════════════════════════════════════════╗{Style.RESET_ALL}
{Fore.YELLOW}║{Style.RESET_ALL}                                                {Fore.YELLOW}║{Style.RESET_ALL}
{Fore.YELLOW}║{Style.RESET_ALL}   {Fore.CYAN}{Style.BRIGHT}██╗     ██╗████████╗{Style.RESET_ALL}                         {Fore.YELLOW}║{Style.RESET_ALL}
{Fore.YELLOW}║{Style.RESET_ALL}   {Fore.CYAN}{Style.BRIGHT}██║     ██║╚══██╔══╝{Style.RESET_ALL}                         {Fore.YELLOW}║{Style.RESET_ALL}
{Fore.YELLOW}║{Style.RESET_ALL}   {Fore.CYAN}{Style.BRIGHT}██║     ██║   ██║   {Style.RESET_ALL}                         {Fore.YELLOW}║{Style.RESET_ALL}
{Fore.YELLOW}║{Style.RESET_ALL}   {Fore.CYAN}{Style.BRIGHT}██║     ██║   ██║   {Style.RESET_ALL}                         {Fore.YELLOW}║{Style.RESET_ALL}
{Fore.YELLOW}║{Style.RESET_ALL}   {Fore.CYAN}{Style.BRIGHT}███████╗██║   ██║   {Style.RESET_ALL}                         {Fore.YELLOW}║{Style.RESET_ALL}
{Fore.YELLOW}║{Style.RESET_ALL}   {Fore.CYAN}{Style.BRIGHT}╚══════╝╚═╝   ╚═╝   {Style.RESET_ALL}                         {Fore.YELLOW}║{Style.RESET_ALL}
{Fore.YELLOW}║{Style.RESET_ALL}                                                {Fore.YELLOW}║{Style.RESET_ALL}
{Fore.YELLOW}║{Style.RESET_ALL}   {Fore.WHITE}{Style.BRIGHT}A Git-like Version Control System{Style.RESET_ALL}            {Fore.YELLOW}║{Style.RESET_ALL}
{Fore.YELLOW}║{Style.RESET_ALL}           {Fore.GREEN}by Flambeau Iriho{Style.RESET_ALL}                    {Fore.YELLOW}║{Style.RESET_ALL}
{Fore.YELLOW}║{Style.RESET_ALL}                                                {Fore.YELLOW}║{Style.RESET_ALL}
{Fore.YELLOW}╚════════════════════════════════════════════════╝{Style.RESET_ALL}
"""


def success(message: str) -> str:
    """Format success message in green."""
    return f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}"


def info(message: str) -> str:
    """Format info message in cyan."""
    return f"{Fore.CYAN}→ {message}{Style.RESET_ALL}"


def warning(message: str) -> str:
    """Format warning message in yellow."""
    return f"{Fore.YELLOW}⚠ {message}{Style.RESET_ALL}"


def error(message: str) -> str:
    """Format error message in red."""
    return f"{Fore.RED}✗ {message}{Style.RESET_ALL}"
