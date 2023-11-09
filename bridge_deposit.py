"""
Bridges USDC from Avalanche to Hubblenet on mainnet. It makes 2 transactions - one to approve USDC transfer to HGTRemote contract, and another to deposit USDC to HGTRemote contract. The deposit transaction also sends some USDC to the hubblenet to be used for gas.

Usage:
```
export PRIVATE_KEY="<private key>"
export HUBBLENET_USER_ADDRESS="<address on hubblenet>"
export DEPOSIT_AMOUNT=100  # total deposit amount in USDC
export GAS_AMOUNT=5  # amount of gas to send to hubblenet in USDC

python bridge_deposit.py
```

in the above example, 95 USDC will be deposited to margin account, and 5 USDC will be sent to the hubblenet to be used for gas.
"""

import asyncio
import json
import os

from eth_abi import encode
from web3 import AsyncHTTPProvider, AsyncWeb3
from web3.constants import ADDRESS_ZERO
from web3.middleware import async_geth_poa_middleware
from web3.middleware.async_cache import _async_simple_cache_middleware

from hubble_exchange.utils import float_to_scaled_int

RPC_ENDPOINT = "https://api.avax.network/ext/bc/C/rpc"

HERE = os.path.dirname(__file__)
with open(f"{HERE}/hubble_exchange/contract_abis/HGTRemote.json", 'r') as abi_file:
    abi_str = abi_file.read()
    HGT_REMOTE_ABI = json.loads(abi_str)

with open(f"{HERE}/hubble_exchange/contract_abis/IERC20.json", 'r') as abi_file:
    abi_str = abi_file.read()
    IERC20_ABI = json.loads(abi_str)

USDC_ON_AVALANCHE = "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E"
HGT_REMOTE = "0x52c1c6936Fca7eb44E086fbAb1e1258E57B5d346"

async def main():
    hubblenet_user_address = os.getenv("HUBBLENET_USER_ADDRESS")
    if not hubblenet_user_address:
        raise ValueError("HUBBLENET_USER_ADDRESS environment variable not set")

    pk = os.getenv("PRIVATE_KEY")
    if not pk:
        raise ValueError("PRIVATE_KEY environment variable not set")

    deposit_amount = os.getenv("DEPOSIT_AMOUNT")
    if not deposit_amount:
        raise ValueError("DEPOSIT_AMOUNT environment variable not set")
    gas_amount = os.getenv("GAS_AMOUNT")
    if not gas_amount:
        raise ValueError("GAS_AMOUNT environment variable not set")

    gas_amount = float_to_scaled_int(float(gas_amount), 6)
    deposit_amount = float_to_scaled_int(float(deposit_amount), 6)
    print("deposit amount: ", deposit_amount)
    print("gas amount: ", gas_amount)

    web3_client = AsyncWeb3(AsyncHTTPProvider(RPC_ENDPOINT))
    web3_client.middleware_onion.inject(async_geth_poa_middleware, layer=0)

    web3_client.middleware_onion.add(_async_simple_cache_middleware, name="cache")

    wallet = web3_client.eth.account.from_key(pk)

    hgt_remote = web3_client.eth.contract(address=HGT_REMOTE, abi=HGT_REMOTE_ABI)
    usdc = web3_client.eth.contract(address=USDC_ON_AVALANCHE, abi=IERC20_ABI)

    depositVars = {
        "to": hubblenet_user_address,
        "tokenIdx": 0,
        "amount": deposit_amount,
        "toGas": gas_amount,
        "isInsuranceFund": False,
        "refundAddress": hubblenet_user_address,
        "zroPaymentAddress": ADDRESS_ZERO,
        "adapterParams": b'',  # default adapter params
    }

    l0_fee = await hgt_remote.functions.estimateSendFee(depositVars).call()
    print("l0 fee: ", l0_fee)

    nonce = await web3_client.eth.get_transaction_count(wallet.address)
    tx = await usdc.functions.approve(HGT_REMOTE, deposit_amount).build_transaction({
        "from": wallet.address,
        "nonce": nonce
    })
    signed_tx = web3_client.eth.account.sign_transaction(tx, pk)
    tx_hash = await web3_client.eth.send_raw_transaction(signed_tx.rawTransaction)
    print("USDC approve tx hash: ", tx_hash.hex())
    await web3_client.eth.wait_for_transaction_receipt(tx_hash)

    tx = await hgt_remote.functions.deposit(depositVars).build_transaction({
        "from": wallet.address,
        "value": l0_fee[0],
        "nonce": nonce + 1,
    })
    signed_tx = web3_client.eth.account.sign_transaction(tx, pk)
    tx_hash = await web3_client.eth.send_raw_transaction(signed_tx.rawTransaction)
    print("deposit tx hash: ", tx_hash.hex())
    await web3_client.eth.wait_for_transaction_receipt(tx_hash)
    return

if __name__ == "__main__":
    asyncio.run(main())
