"""期货数据和技术指标模块"""

from kairos.futures.config import load_contracts, CONTRACTS
from kairos.futures.data_fetcher import get_historical_data, get_multi_timeframe_data
from kairos.futures.data_cache import (
    save_historical_data, save_multi_timeframe_data,
    load_historical_data, load_multi_timeframe_data,
    has_cached_data, list_cached_contracts
)
from kairos.futures.indicators import calc_all_indicators
from kairos.futures.indicators_advanced import calc_obv, calc_adx
from kairos.futures.indicators_mtf import calc_multi_timeframe_indicators, get_timeframe_alignment
from kairos.futures.divergence import detect_divergence
from kairos.futures.display import get_daily_output_dir

__all__ = [
    "load_contracts",
    "CONTRACTS",
    "get_historical_data",
    "get_multi_timeframe_data",
    "save_historical_data",
    "save_multi_timeframe_data",
    "load_historical_data",
    "load_multi_timeframe_data",
    "has_cached_data",
    "list_cached_contracts",
    "calc_all_indicators",
    "calc_multi_timeframe_indicators",
    "get_timeframe_alignment",
    "calc_obv",
    "calc_adx",
    "detect_divergence",
    "get_daily_output_dir",
]

