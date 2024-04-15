import logging

import requests
from requests.exceptions import HTTPError, Timeout

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def request_third_party_transaction(
    wallet,
    amount,
    transaction_type,
    api_url="http://third_party_service:8010",
    timeout=10,
):

    data = {
        "wallet_uuid": str(wallet.uuid),
        "amount": amount,
        "type": transaction_type,
    }
    try:
        response = requests.post(api_url, json=data, timeout=timeout)
        response.raise_for_status()
        logging.info(
            "Successful "
            + transaction_type
            + " transaction for wallet "
            + str(wallet.uuid)
            + " of amount "
            + str(amount)
        )
        return response
    except Timeout as e:
        logging.error(f"Timeout occurred: {e}")
        raise Timeout(
            f"Request to {api_url} timed out after {timeout} seconds."
        )
    except HTTPError as e:
        logging.error(f"HTTP error occurred: {e}")
        raise HTTPError(f"Failed due to HTTP error: {e}")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise Exception(f"An unexpected error occurred: {e}")
