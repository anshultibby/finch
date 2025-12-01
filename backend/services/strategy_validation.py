"""
Strategy Validation Service - Validates trading strategy definitions

The main chat agent structures strategies directly.
This service only provides validation logic.
"""
import logging
from typing import Dict, Any
from models.strategy import TradingStrategy

logger = logging.getLogger(__name__)


class StrategyValidationService:
    """Service to validate trading strategy definitions"""
    
    def __init__(self):
        pass
    
    @staticmethod
    def validate_strategy(strategy: TradingStrategy) -> Dict[str, Any]:
        """
        Validate a strategy definition and return validation results
        
        Returns:
            Dict with 'valid' (bool) and 'issues' (list) keys
        """
        issues = []
        
        # Check for required data
        if not strategy.data_requirements:
            issues.append("Strategy must specify data requirements")
        
        # Check for entry conditions
        if not strategy.entry_conditions:
            issues.append("Strategy must have at least one entry condition")
        
        # Check for exit conditions or risk parameters
        if not strategy.exit_conditions and not strategy.risk_parameters.stop_loss_pct:
            issues.append("Strategy must have exit conditions or stop loss")
        
        # Validate condition fields are reasonable
        for condition in strategy.entry_conditions + strategy.exit_conditions:
            if not condition.field:
                issues.append(f"Condition missing field name")
            if condition.value is None:
                issues.append(f"Condition '{condition.field}' missing value")
        
        # Check risk parameters are reasonable
        if strategy.risk_parameters.stop_loss_pct and strategy.risk_parameters.stop_loss_pct > 50:
            issues.append("Stop loss > 50% is unreasonably high")
        
        if strategy.risk_parameters.position_size_pct > 50:
            issues.append("Position size > 50% is unreasonably high")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }

