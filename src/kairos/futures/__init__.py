"""期货数据和技术指标模块"""

from kairos.futures.config import load_contracts, CONTRACTS
from kairos.futures.data_fetcher import get_historical_data
from kairos.futures.indicators import calc_all_indicators
from kairos.futures.divergence import detect_divergence
from kairos.futures.display import get_daily_output_dir

__all__ = [
    "load_contracts",
    "CONTRACTS",
    "get_historical_data",
    "calc_all_indicators",
    "detect_divergence",
    "get_daily_output_dir",
]

