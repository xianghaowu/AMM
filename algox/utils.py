from base64 import b64decode
from typing import Any, Dict, List, Optional, Union

from algosdk.v2client.algod import AlgodClient


def get_algod_client(url, api_key) -> AlgodClient:
    headers = {
        'X-API-Key': api_key
    }
    return AlgodClient(api_key, url, headers)


class PendingTxnResponse:
    def __init__(self, response: Dict[str, Any]) -> None:
        self.poolError: str = response["pool-error"]
        self.txn: Dict[str, Any] = response["txn"]

        self.application_index: Optional[int] = response.get(
            "application-index")
        self.asset_index: Optional[int] = response.get("asset-index")
        self.close_rewards: Optional[int] = response.get("close-rewards")
        self.closing_amount: Optional[int] = response.get("closing-amount")
        self.confirmed_round: Optional[int] = response.get("confirmed-round")
        self.global_state_delta: Optional[Any] = response.get(
            "global-state-delta")
        self.local_state_delta: Optional[Any] = response.get(
            "local-state-delta")
        self.receiver_rewards: Optional[int] = response.get("receiver-rewards")
        self.sender_rewards: Optional[int] = response.get("sender-rewards")

        self.inner_txns: List[Any] = response.get("inner-txns", [])
        self.logs: List[bytes] = [b64decode(ll)
                                  for ll in response.get("logs", [])]


def wait_for_transaction(
        client: AlgodClient, tx_id: str
) -> PendingTxnResponse:
    last_status = client.status()
    last_round = last_status.get("last-round")
    pending_txn = client.pending_transaction_info(tx_id)
    while not (pending_txn.get("confirmed-round") and pending_txn.get("confirmed-round") > 0):
        print("Waiting for confirmation...")
        last_round += 1
        client.status_after_block(last_round)
        pending_txn = client.pending_transaction_info(tx_id)
    print(
        "Transaction {} confirmed in round {}.".format(
            tx_id, pending_txn.get("confirmed-round")
        )
    )
    return PendingTxnResponse(pending_txn)


def decode_state(state_array: List[Any]) -> Dict[bytes, Union[int, bytes]]:
    state: Dict[bytes, Union[int, bytes]] = dict()

    for pair in state_array:
        key = b64decode(pair["key"])

        value = pair["value"]
        value_type = value["type"]

        if value_type == 2:
            # value is uint64
            value = value.get("uint", 0)
        elif value_type == 1:
            # value is byte array
            value = b64decode(value.get("bytes", ""))
        else:
            raise Exception(f"Unexpected state type: {value_type}")

        state[key] = value

    return state


def get_app_global_state(
        client: AlgodClient, app_id: int
) -> Dict[bytes, Union[int, bytes]]:
    app_info = client.application_info(app_id)
    return decode_state(app_info["params"]["global-state"])


def fully_compile_contract(client: AlgodClient, teal: str) -> bytes:
    response = client.compile(teal)
    return b64decode(response["result"])
