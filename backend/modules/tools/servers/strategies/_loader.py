"""
Strategy Loader - Dynamically load user strategies from database files

Strategies are stored as ChatFiles and loaded into memory at runtime.
Supports hot-reloading when strategy code changes.
"""
import json
import importlib.util
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import tempfile
import os

from crud.chat_files import get_chat_file
from sqlalchemy.ext.asyncio import AsyncSession
from ._base import BaseStrategy, StrategyConfig


class StrategyLoader:
    """
    Loads user strategies from database files
    
    Each strategy is a collection of ChatFiles:
    - strategy.py: Main strategy class inheriting from BaseStrategy
    - config.json: Configuration (platform, polling, risk limits)
    - (optional) utils.py, indicators.py, etc.
    """
    
    def __init__(self):
        self._cache: Dict[str, BaseStrategy] = {}
        self._file_hashes: Dict[str, str] = {}
    
    async def load_strategy(
        self,
        db: AsyncSession,
        strategy_id: str,
        file_ids: list[str]
    ) -> BaseStrategy:
        """
        Load a strategy from database files
        
        Args:
            db: Database session
            strategy_id: Strategy ID
            file_ids: List of ChatFile IDs containing strategy code
            
        Returns:
            Instantiated BaseStrategy subclass
        """
        # Check cache
        cache_key = f"{strategy_id}_{','.join(file_ids)}"
        if cache_key in self._cache:
            # TODO: Check if files have changed (compare hashes)
            return self._cache[cache_key]
        
        # Load files from database
        files = {}
        for file_id in file_ids:
            file_record = await get_chat_file(db, file_id)
            if file_record:
                files[file_record.filename] = file_record.file_content
        
        if not files:
            raise ValueError(f"No files found for strategy {strategy_id}")
        
        # Validate required files
        if 'config.json' not in files:
            raise ValueError("Strategy must have config.json")
        if 'strategy.py' not in files:
            raise ValueError("Strategy must have strategy.py")
        
        # Parse config
        config_data = json.loads(files['config.json'])
        config = StrategyConfig(**config_data)
        
        # Load strategy module dynamically
        strategy_class = self._load_strategy_module(files, strategy_id)
        
        # Instantiate strategy
        strategy_instance = strategy_class(config)
        
        # Cache it
        self._cache[cache_key] = strategy_instance
        
        return strategy_instance
    
    def _load_strategy_module(self, files: Dict[str, str], strategy_id: str) -> type[BaseStrategy]:
        """
        Dynamically load strategy Python module from string
        
        Creates a temporary module namespace and executes strategy.py
        """
        # Create temporary directory for files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            
            # Write all Python files to temp dir
            for filename, content in files.items():
                if filename.endswith('.py'):
                    (tmp_path / filename).write_text(content)
            
            # Load strategy.py as module
            module_name = f"user_strategy_{strategy_id}"
            spec = importlib.util.spec_from_file_location(
                module_name,
                tmp_path / "strategy.py"
            )
            
            if spec is None or spec.loader is None:
                raise ValueError("Failed to load strategy.py")
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            
            try:
                spec.loader.exec_module(module)
            except Exception as e:
                raise ValueError(f"Error executing strategy.py: {e}")
            
            # Find BaseStrategy subclass
            strategy_class = None
            for name in dir(module):
                obj = getattr(module, name)
                if (isinstance(obj, type) and 
                    issubclass(obj, BaseStrategy) and 
                    obj is not BaseStrategy):
                    strategy_class = obj
                    break
            
            if strategy_class is None:
                raise ValueError("No BaseStrategy subclass found in strategy.py")
            
            return strategy_class
    
    def invalidate_cache(self, strategy_id: str):
        """Invalidate cache for a strategy (e.g., when code changes)"""
        self._cache = {
            k: v for k, v in self._cache.items()
            if not k.startswith(f"{strategy_id}_")
        }


# Global loader instance
_loader: Optional[StrategyLoader] = None


def get_strategy_loader() -> StrategyLoader:
    """Get or create global strategy loader"""
    global _loader
    if _loader is None:
        _loader = StrategyLoader()
    return _loader
