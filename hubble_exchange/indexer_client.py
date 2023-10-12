
import os

import requests

from hubble_exchange.constants import get_allowed_candle_intervals


class IndexerClient:
    def __init__(self):
        indexer_api_url = os.getenv("HUBBLE_INDEXER_API_URL")
        if not indexer_api_url:
            raise ValueError("HUBBLE_INDEXER_API_URL environment variable not set")
        self.indexer_api_url = indexer_api_url

    def get_candles(self, market_name, interval, start_time, end_time):
        allowed_intervals = get_allowed_candle_intervals()

        if interval not in allowed_intervals:
            raise ValueError(f"Interval {interval} not allowed. Allowed intervals are {allowed_intervals}")

        url = f"{self.indexer_api_url}/market/{market_name}/chart?timeframe={interval}&start={start_time}&end={end_time}&showEmpty=true"

        response = requests.get(url)
        return response.json()

    def get_predicted_funding_rate(self, market_name):
        url = f"{self.indexer_api_url}/market/{market_name}/predicted_funding_rate"
        response = requests.get(url)
        return response.json()

    def get_historical_funding_rate(self, market_name, timestamp):
        url = f"{self.indexer_api_url}/market/{market_name}/funding_rate?timestamp={timestamp}"
        response = requests.get(url)
        return response.json()

    def get_historical_open_interest(self, market_name, timestamp):
        url = f"{self.indexer_api_url}/market/{market_name}/open_interest?timestamp={timestamp}"
        response = requests.get(url)
        return response.json()
