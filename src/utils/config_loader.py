"""Configuration loader with environment variable substitution."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any
import logging
import re

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Load and validate configuration from YAML file."""

    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize configuration loader.

        Args:
            config_path: Path to configuration YAML file
        """
        self.config_path = Path(config_path)

    def load(self) -> Dict[str, Any]:
        """Load configuration with environment variable substitution.

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid YAML
        """
        if not self.config_path.exists():
            # Try example file
            example_path = Path(str(self.config_path) + ".example")
            if example_path.exists():
                logger.warning(
                    f"Config file not found: {self.config_path}. "
                    f"Using example: {example_path}"
                )
                self.config_path = example_path
            else:
                raise FileNotFoundError(
                    f"Configuration file not found: {self.config_path}"
                )

        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Substitute environment variables
        config = self._substitute_env_vars(config)

        # Validate configuration
        self._validate(config)

        logger.info(f"Configuration loaded from: {self.config_path}")
        return config

    def _substitute_env_vars(self, config: Any) -> Any:
        """Recursively substitute environment variables in config.

        Substitutes ${VAR_NAME} or ${VAR_NAME:default} patterns.

        Args:
            config: Configuration dict or value

        Returns:
            Config with substituted values
        """
        if isinstance(config, dict):
            return {k: self._substitute_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]
        elif isinstance(config, str):
            return self._substitute_string(config)
        else:
            return config

    def _substitute_string(self, value: str) -> str:
        """Substitute environment variables in string.

        Args:
            value: String potentially containing ${VAR} patterns

        Returns:
            String with substituted values
        """
        # Pattern: ${VAR_NAME} or ${VAR_NAME:default_value}
        pattern = r'\$\{([A-Z_][A-Z0-9_]*?)(?::([^}]*))?\}'

        def replace(match):
            var_name = match.group(1)
            default = match.group(2) if match.group(2) is not None else ""

            env_value = os.getenv(var_name)

            if env_value is None:
                if default:
                    logger.debug(
                        f"Environment variable {var_name} not set, "
                        f"using default: {default}"
                    )
                    return default
                else:
                    logger.warning(
                        f"Environment variable {var_name} not set and no default provided"
                    )
                    return match.group(0)  # Return original if no default

            return env_value

        return re.sub(pattern, replace, value)

    def _validate(self, config: Dict) -> None:
        """Validate configuration has required fields.

        Args:
            config: Configuration dictionary

        Raises:
            ValueError: If required fields are missing or invalid
        """
        required_sections = ['directories', 'api', 'xmp', 'workflow', 'logging']

        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required config section: {section}")

        # Validate directories exist or can be created
        directories = config['directories']
        for name in ['inbox', 'sorted', 'working']:
            if name not in directories:
                raise ValueError(f"Missing required directory config: {name}")

            path = Path(directories[name])
            if not path.exists():
                logger.warning(
                    f"Directory does not exist: {path}. "
                    "It will be created on first run."
                )

        # Validate API keys are set (warn if not)
        saucenao_key = config['api']['saucenao'].get('api_key', '')
        if not saucenao_key or '${' in saucenao_key:
            logger.warning(
                "SauceNAO API key not configured. "
                "Reverse image search will be disabled."
            )

        danbooru_key = config['api']['danbooru'].get('api_key', '')
        if not danbooru_key or '${' in danbooru_key:
            logger.warning(
                "Danbooru API key not configured. "
                "Tag extraction may be limited."
            )

        logger.debug("Configuration validation passed")


def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """Convenience function to load configuration.

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary
    """
    loader = ConfigLoader(config_path)
    return loader.load()
