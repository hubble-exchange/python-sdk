import os
import math
import random
import time
from eth_typing import Address
from eth_account import Account


rpc_endpoint = ""
websocket_endpoint = ""


def float_to_scaled_int(val: float, scale: int) -> int:
    big_float = math.floor(val * (10 ** scale))
    return int(big_float)


def get_address_from_private_key(private_key: str) -> Address:
    account = Account.from_key(private_key)
    return account.address

def get_new_salt() -> int:
    return int(str(time.time_ns()) + str(random.randint(0, 10000)))


def get_rpc_endpoint() -> str:
    global rpc_endpoint
    if not rpc_endpoint:
        rpc_host = os.getenv("HUBBLE_RPC_HOST")
        if not rpc_host:
            raise ValueError("HUBBLE_RPC_HOST environment variable not set")
        blockchain_id = os.getenv("HUBBLE_BLOCKCHAIN_ID")
        if not blockchain_id:
            raise ValueError("HUBBLE_BLOCKCHAIN_ID environment variable not set")
        path = f"/ext/bc/{blockchain_id}/rpc"
        rpc_endpoint = f"https://{rpc_host}{path}"
    return rpc_endpoint


def get_websocket_endpoint() -> str:
    global websocket_endpoint
    if not websocket_endpoint:
        rpc_host = os.getenv("HUBBLE_RPC_HOST")
        if not rpc_host:
            raise ValueError("HUBBLE_RPC_HOST environment variable not set")
        blockchain_id = os.getenv("HUBBLE_BLOCKCHAIN_ID")
        if not blockchain_id:
            raise ValueError("HUBBLE_BLOCKCHAIN_ID environment variable not set")
        path = f"/ext/bc/{blockchain_id}/ws"
        websocket_endpoint = f"wss://{rpc_host}{path}"
    return websocket_endpoint
