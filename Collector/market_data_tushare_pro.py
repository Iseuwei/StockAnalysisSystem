import pandas as pd
import tushare as ts
from datetime import date

from os import sys, path
root_path = path.dirname(path.dirname(path.abspath(__file__)))

try:
    import config
    from Utiltity.common import *
    from Utiltity.time_utility import *
    from Collector.CollectorUtility import *
except Exception as e:
    sys.path.append(root_path)

    import config
    from Utiltity.common import *
    from Utiltity.time_utility import *
    from Collector.CollectorUtility import *
finally:
    pass

ts.set_token(config.TS_TOKEN)


# -------------------------------------------------------- Prob --------------------------------------------------------

CAPACITY_LIST = [
    'Market.TradeCalender',
    'Market.NamingHistory',
    'Market.SecuritiesInfo',
    'Market.IndexComponent',
]


def plugin_prob() -> dict:
    return {
        'plugin_name': 'market_data_tushare_pro',
        'plugin_version': '0.0.0.1',
        'tags': ['tusharepro']
    }


def plugin_adapt(uri: str) -> bool:
    return uri in CAPACITY_LIST


def plugin_capacities() -> list:
    return CAPACITY_LIST


# ----------------------------------------------------------------------------------------------------------------------

def __fetch_trade_calender(**kwargs) -> pd.DataFrame or None:
    exchange = kwargs.get('exchange', '')
    if str_available(exchange) and exchange not in ['SSE', 'SZSE', 'A-SHARE']:
        return None

    result = check_execute_test_flag(**kwargs)
    if result is None:
        time_serial = kwargs.get('trade_date', None)
        since, until = normalize_time_serial(time_serial, text2date('1900-01-01'), today())

        ts_since = since.strftime('%Y%m%d')
        ts_until = until.strftime('%Y%m%d')

        pro = ts.pro_api()
        # If we specify the exchange parameter, it raises error.
        result = pro.trade_cal('', start_date=ts_since, end_date=ts_until)
    check_execute_dump_flag(result, **kwargs)

    if result is not None:
        result.rename(columns={'exchange': 'exchange', 'cal_date': 'trade_date', 'is_open': 'status'}, inplace=True)
        # Because tushare only support SSE and they are the same
        if exchange == 'SZSE' or exchange == 'A-SHARE':
            result.drop(result[result.exchange != 'SSE'].index, inplace=True)
            result['exchange'] = exchange
        else:
            result.drop(result[result.exchange != exchange].index, inplace=True)
        result['trade_date'] = pd.to_datetime(result['trade_date'])
    return result


def __fetch_naming_history(**kwargs):
    result = check_execute_test_flag(**kwargs)
    if result is None:
        ts_code = pickup_ts_code(kwargs)
        period = kwargs.get('naming_date')
        since, until = normalize_time_serial(period, text2date('1900-01-01'), today())

        ts_since = since.strftime('%Y%m%d')
        ts_until = until.strftime('%Y%m%d')

        pro = ts.pro_api()
        result = pro.namechange(ts_code=ts_code, start_date=ts_since, end_date=ts_until,
                                fields='ts_code,name,start_date,end_date,ann_date,change_reason')
    check_execute_dump_flag(result, **kwargs)

    if result is not None:
        if 'start_date' in result.columns:
            result['naming_date'] = pd.to_datetime(result['start_date'], format='%Y-%m-%d')
        if 'stock_identity' not in result.columns:
            result['stock_identity'] = result['ts_code'].apply(ts_code_to_stock_identity)

    return result


def __fetch_securities_info(**kwargs) -> pd.DataFrame or None:
    result = check_execute_test_flag(**kwargs)
    if result is None:
        pro = ts.pro_api()
        # If we specify the exchange parameter, it raises error.
        result = pro.stock_basic(fields='ts_code,symbol,name,area,industry,fullname,list_date,'
                                        'enname,market,exchange,curr_type,list_status,list_date,delist_date,is_hs')
    check_execute_dump_flag(result, **kwargs)

    if result is not None:
        result.rename(columns={'curr_type': 'currency',
                               'list_date': 'listing_date',
                               'delist_date': 'delisting_date'}, inplace=True)

        if 'listing_date' in result.columns:
            result['listing_date'] = pd.to_datetime(result['listing_date'], format='%Y-%m-%d')
        if 'delisting_date' in result.columns:
            result['delisting_date'] = pd.to_datetime(result['delisting_date'], format='%Y-%m-%d')

        if 'code' not in result.columns:
            result['code'] = result['ts_code'].apply(lambda val: val.split('.')[0])
        if 'exchange' not in result.columns:
            result['exchange'] = result['ts_code'].apply(lambda val: val.split('.')[1])
            result['exchange'] = result['exchange'].apply(lambda val: 'SSE' if val == 'SH' else val)
            result['exchange'] = result['exchange'].apply(lambda val: 'SZSE' if val == 'SZ' else val)
        result['stock_identity'] = result['code'] + '.' + result['exchange']

    return result


# ----------------------------------------------------------------------------------------------------------------------

def query(**kwargs) -> pd.DataFrame or None:
    uri = kwargs.get('uri')
    if uri == 'Market.TradeCalender':
        return __fetch_trade_calender(**kwargs)
    elif uri == 'Market.NamingHistory':
        return __fetch_naming_history(**kwargs)
    elif uri == 'Market.SecuritiesInfo':
        return __fetch_securities_info(**kwargs)
    elif uri == 'Market.IndexComponent':
        return None
    else:
        return None


def validate(**kwargs) -> bool:
    nop(kwargs)
    return True



