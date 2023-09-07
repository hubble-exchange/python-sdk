# dynamically import config from the provided config module
def init_config(config_module):
    for attr_name in dir(config_module):
        if not attr_name.startswith("_"):  # skip internal names
            globals()[attr_name] = getattr(config_module, attr_name)


def get_minimum_quantity(market: int) -> int:
    try:
        return min_quantity[market]
    except KeyError:
        raise ValueError(f"Market {market} does not exist")


def get_price_precision(market: int) -> int:
    try:
        return price_precision[market]
    except KeyError:
        raise ValueError(f"Market {market} does not exist")
