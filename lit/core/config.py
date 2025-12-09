"""Configuration management for Lit VCS.

This module provides a clean interface for reading and writing
both repository-local and global configuration files.
"""

import os
import configparser
from pathlib import Path
from typing import Optional, Dict, Any


class Config:
    """
    Manages Lit configuration files.
    
    Configuration is stored in INI format, similar to Git:
    - Global config: ~/.litconfig
    - Repository config: .lit/config
    
    Repository config takes precedence over global config.
    Environment variables take highest precedence.
    """
    
    GLOBAL_CONFIG_PATH = Path.home() / '.litconfig'
    
    def __init__(self, repo_config_path: Optional[Path] = None):
        """
        Initialize Config manager.
        
        Args:
            repo_config_path: Path to repository config file, if in a repo
        """
        self.repo_config_path = repo_config_path
        self._global_config = None
        self._repo_config = None
    
    @property
    def global_config(self) -> configparser.ConfigParser:
        """Load and return global configuration."""
        if self._global_config is None:
            self._global_config = configparser.ConfigParser()
            if self.GLOBAL_CONFIG_PATH.exists():
                self._global_config.read(self.GLOBAL_CONFIG_PATH)
        return self._global_config
    
    @property
    def repo_config(self) -> Optional[configparser.ConfigParser]:
        """Load and return repository configuration."""
        if self._repo_config is None and self.repo_config_path:
            self._repo_config = configparser.ConfigParser()
            if self.repo_config_path.exists():
                self._repo_config.read(self.repo_config_path)
        return self._repo_config
    
    def get(self, section: str, key: str, fallback: Optional[str] = None) -> Optional[str]:
        """
        Get a configuration value.
        
        Priority order (highest to lowest):
        1. Environment variables (LIT_<SECTION>_<KEY>)
        2. Repository config
        3. Global config
        4. Fallback value
        
        Args:
            section: Config section (e.g., 'user', 'core')
            key: Config key (e.g., 'name', 'email')
            fallback: Default value if not found
            
        Returns:
            Configuration value or fallback
        """
        # Check environment variable first
        env_key = f"LIT_{section.upper()}_{key.upper()}"
        env_value = os.environ.get(env_key)
        if env_value is not None:
            return env_value
        
        # Check repository config
        if self.repo_config and self.repo_config.has_option(section, key):
            return self.repo_config.get(section, key)
        
        # Check global config
        if self.global_config.has_option(section, key):
            return self.global_config.get(section, key)
        
        return fallback
    
    def set(self, section: str, key: str, value: str, global_config: bool = False) -> None:
        """
        Set a configuration value.
        
        Args:
            section: Config section
            key: Config key
            value: Value to set
            global_config: If True, write to global config; otherwise repo config
        """
        if global_config:
            config = self.global_config
            config_path = self.GLOBAL_CONFIG_PATH
        else:
            if not self.repo_config_path:
                raise ValueError("No repository config path available")
            if self._repo_config is None:
                self._repo_config = configparser.ConfigParser()
                if self.repo_config_path.exists():
                    self._repo_config.read(self.repo_config_path)
            config = self._repo_config
            config_path = self.repo_config_path
        
        if not config.has_section(section):
            config.add_section(section)
        
        config.set(section, key, value)
        
        with open(config_path, 'w') as f:
            config.write(f)
    
    def unset(self, section: str, key: str, global_config: bool = False) -> bool:
        """
        Remove a configuration value.
        
        Args:
            section: Config section
            key: Config key
            global_config: If True, modify global config; otherwise repo config
            
        Returns:
            True if value was removed, False if it didn't exist
        """
        if global_config:
            config = self.global_config
            config_path = self.GLOBAL_CONFIG_PATH
        else:
            if not self.repo_config:
                return False
            config = self.repo_config
            config_path = self.repo_config_path
        
        if not config.has_option(section, key):
            return False
        
        config.remove_option(section, key)
        
        # Remove empty sections
        if not config.options(section):
            config.remove_section(section)
        
        with open(config_path, 'w') as f:
            config.write(f)
        
        return True
    
    def list_all(self, global_only: bool = False, repo_only: bool = False) -> Dict[str, Dict[str, str]]:
        """
        List all configuration values.
        
        Args:
            global_only: Only show global config
            repo_only: Only show repo config
            
        Returns:
            Dict of sections to key-value dicts
        """
        result = {}
        
        # Add global config values
        if not repo_only:
            for section in self.global_config.sections():
                if section not in result:
                    result[section] = {}
                for key, value in self.global_config.items(section):
                    result[section][f"{key} (global)"] = value
        
        # Add/override with repo config values
        if not global_only and self.repo_config:
            for section in self.repo_config.sections():
                if section not in result:
                    result[section] = {}
                for key, value in self.repo_config.items(section):
                    result[section][key] = value
        
        return result
    
    def get_user_identity(self) -> tuple:
        """
        Get user name and email for commits.
        
        Returns:
            Tuple of (name, email), either may be None
        """
        name = self.get('user', 'name')
        email = self.get('user', 'email')
        return name, email


def get_config(repo=None) -> Config:
    """
    Get a Config instance.
    
    Args:
        repo: Repository instance, or None for global-only config
        
    Returns:
        Config instance
    """
    if repo:
        return Config(repo.config_file)
    return Config()
