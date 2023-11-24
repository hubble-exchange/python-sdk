"""
Bridges USDC from Hubble Exchange margin account to Avalanche on mainnet.

Usage:
```
export PRIVATE_KEY="<private key>"
export C_CHAIN_USER_ADDRESS="<address on avalanche c-chain>"
export WITHDRAW_AMOUNT=10  # total withdraw amount in USDC. 

python bridge_withdraw.py
```

in the above example, 10 USDC will be deducted from margin account, and be sent to C_CHAIN_USER_ADDRESS on avalanche. There will also be some fee deducted from the hubblenet's native currency(USDC).
"""

import asyncio
import json
import os
import time

from eth_abi import encode
from web3 import AsyncHTTPProvider, AsyncWeb3
from web3.constants import ADDRESS_ZERO
from web3.middleware import async_geth_poa_middleware
from web3.middleware.async_cache import _async_simple_cache_middleware

from hubble_exchange.utils import float_to_scaled_int

RPC_ENDPOINT = "https://nd-125-878-356.hubble.ext.p2pify.com/a056b03e8307044756c0a92ce1dd2f15/ext/bc/2jfjkB7NkK4v8zoaoWmh5eaABNW6ynjQvemPFZpgPQ7ugrmUXv/rpc"

HERE = os.path.dirname(__file__)
with open(f"{HERE}/hubble_exchange/contract_abis/HGT.json", 'r') as abi_file:
    abi_str = abi_file.read()
    HGT_ABI = json.loads(abi_str)

with open(f"{HERE}/hubble_exchange/contract_abis/MarginAccountHelper.json", 'r') as abi_file:
    abi_str = abi_file.read()
    MARGIN_ACCOUNT_HELPER_ABI = json.loads(abi_str)

HGT = "0x74C3986822e15fA4A0Cef6f13FD7BF6FA70ef0ee"
MARGIN_ACCOUNT_HELPER = "0xEdA17223bf959aEfE5D3244EBED1881fe98A3d1d"
L0_CHAIN_ID_C_CHAIN = 106


async def main():
    c_chain_user_address = os.getenv("C_CHAIN_USER_ADDRESS")
    if not c_chain_user_address:
        raise ValueError("C_CHAIN_USER_ADDRESS environment variable not set")

    pk = os.getenv("PRIVATE_KEY")
    if not pk:
        raise ValueError("PRIVATE_KEY environment variable not set")

    withdraw_amount = os.getenv("WITHDRAW_AMOUNT")
    if not withdraw_amount:
        raise ValueError("WITHDRAW_AMOUNT environment variable not set")

    withdraw_amount = float_to_scaled_int(float(withdraw_amount), 6)
    print("withdraw amount: ", withdraw_amount)

    web3_client = AsyncWeb3(AsyncHTTPProvider(RPC_ENDPOINT))
    web3_client.middleware_onion.inject(async_geth_poa_middleware, layer=0)
    web3_client.middleware_onion.add(_async_simple_cache_middleware, name="cache")

    wallet = web3_client.eth.account.from_key(pk)

    hgt = web3_client.eth.contract(address=HGT, abi=HGT_ABI)
    margin_account_helper = web3_client.eth.contract(address=MARGIN_ACCOUNT_HELPER, abi=MARGIN_ACCOUNT_HELPER_ABI)

    adapter_params = encode(['uint16', 'uint'], [1, 400000])[30:]
    # adapter_params = b''  # default params

    withdraw_vars = {
        "dstChainId": L0_CHAIN_ID_C_CHAIN,
        "secondHopChainId": 0,
        "dstPoolId": 0,
        "to": c_chain_user_address,
        "tokenIdx": 0,
        "amount": withdraw_amount,
        "amountMin": withdraw_amount,
        "refundAddress": c_chain_user_address,
        "zroPaymentAddress": ADDRESS_ZERO,
        "adapterParams": adapter_params
    }


    l0_fee = await hgt.functions.estimateSendFee(withdraw_vars).call()
    print("l0 fee: ", l0_fee)

    nonce = await web3_client.eth.get_transaction_count(wallet.address)
    tx = await margin_account_helper.functions.withdrawMarginToChain(
        withdraw_vars["to"],
        withdraw_vars["amount"],
        withdraw_vars["tokenIdx"],
        withdraw_vars["dstChainId"],
        withdraw_vars["secondHopChainId"],
        withdraw_vars["amountMin"],
        withdraw_vars["dstPoolId"],
        withdraw_vars["adapterParams"]
    ).build_transaction({
        "from": wallet.address,
        "value": l0_fee[0],
        "nonce": nonce,
    })
    signed_tx = web3_client.eth.account.sign_transaction(tx, pk)
    tx_hash = await web3_client.eth.send_raw_transaction(signed_tx.rawTransaction)
    print("withdraw tx hash on hubblenet: ", tx_hash.hex())
    print(f'you can go to https://layerzeroscan.com/tx/{tx_hash.hex()} to check the status of the transaction')
    await web3_client.eth.wait_for_transaction_receipt(tx_hash)
    return

if __name__ == "__main__":
    asyncio.run(main())
