"""Kairos - 期货交易技术分析和决策系统"""

__version__ = "0.2.0"
__author__ = "Kairos Team"

from kairos.futures.config import load_contracts, CONTRACTS
from kairos.futures.data_fetcher import get_historical_data
from kairos.futures.indicators import calc_all_indicators
from kairos.futures.divergence import detect_divergence
from kairos.analyzer import run_full_analysis
from kairos.contracts import update_contracts

__all__ = [
    "load_contracts",
    "CONTRACTS",
    "get_historical_data",
    "calc_all_indicators",
    "detect_divergence",
    "run_full_analysis",
    "update_contracts",
]

