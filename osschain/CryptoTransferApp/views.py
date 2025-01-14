from django.http import JsonResponse
import json
from web3 import Web3
from django.core.cache import cache
import time
from osschain.client_rescrict import is_rate_limited, get_client_ip

ERC20_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    }
]

def retry_on_specific_error(func, retries=5, delay=1):
    specific_error_message = "{'code': -32602, 'message': 'too many arguments, want at most 1'}"
    
    for attempt in range(retries):
        try:
            return func()
        except Exception as e:
            error_message = str(e)
            if specific_error_message in error_message:
                print(f"Error occurred: {error_message}. Retrying {attempt + 1}/{retries}")
                time.sleep(delay)
            else:
                # თუ ერორი განსხვავებულია, გამოდის retry მექანიზმიდან
                raise e
    raise Exception("Exceeded maximum retries with error: " + error_message)

def fetch_native_currency(blockchain):
    known_blockchains = {
        'ethereum': 'ETH',
        'polygon': 'MATIC',
        'bsc': 'BNB',
        'avalanche': 'AVAX',
        'optimism': 'OP',
        # Add more known blockchains and their native currencies here
    }
    return known_blockchains.get(blockchain.lower(), 'UNKNOWN')

def calculate_chain_gas_price(request):
    if request.method == 'POST':
        user_ip = get_client_ip(request)
        user_key = f"rate_limit_{user_ip}_calculate_chain_gas_price"

        if is_rate_limited(user_key):
            return JsonResponse({'success': False, 'error': 'Rate limit exceeded. Try again later.'}, status=429)

        try:
            data = json.loads(request.body.decode('utf-8'))
            sender_address = data.get('sender_address')
            receiver_address = data.get('receiver_address')
            amount = data.get('amount')
            blockchain = data.get('blockchain')

            if not all([sender_address, receiver_address, amount, blockchain]):
                return JsonResponse({'success': False, 'error': 'Missing required fields'}, status=400)

            rpc_url = f'https://rpc.ankr.com/{blockchain}/f7c0df84b43c7f9f2c529c76efc01da4b30271a66608da4728f9830ea17d29bc'
            web3 = Web3(Web3.HTTPProvider(rpc_url))

            if not web3.is_connected():
                return JsonResponse({'success': False, 'error': 'Failed to connect to blockchain node'}, status=500)

            def build_and_estimate_gas():
                amount_in_wei = web3.to_wei(amount, 'ether')
                transaction = {
                    'from': sender_address,
                    'to': receiver_address,
                    'value': amount_in_wei
                }
                gas_estimate = web3.eth.estimate_gas(transaction)
                gas_price = web3.eth.gas_price
                gas_fee_wei = gas_estimate * gas_price
                gas_fee_native = web3.from_wei(gas_fee_wei, 'ether')
                native_currency = fetch_native_currency(blockchain)
                return {
                    'gas_fee_wei': gas_fee_wei,
                    'gas_fee_native': float(gas_fee_native),
                    'native_currency': native_currency
                }

            result = retry_on_specific_error(build_and_estimate_gas)
            return JsonResponse({'success': True, **result})

        except Exception as e:
            print(f"Error: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
    
def calculate_token_gas_price(request):
    if request.method == 'POST':
        user_ip = get_client_ip(request)
        user_key = f"rate_limit_{user_ip}_calculate_chain_gas_price"

        if is_rate_limited(user_key):
            return JsonResponse({'success': False, 'error': 'Rate limit exceeded. Try again later.'}, status=429)
        try:
            data = json.loads(request.body.decode('utf-8'))
            sender_address = data.get('sender_address')
            receiver_address = data.get('receiver_address')
            amount = data.get('amount')
            blockchain = data.get('blockchain')
            token_contract_address = data.get('token_contract_address')

            if not all([sender_address, receiver_address, amount, blockchain, token_contract_address]):
                return JsonResponse({'success': False, 'error': 'Missing required fields'}, status=400)

            rpc_url = f'https://rpc.ankr.com/{blockchain}/f7c0df84b43c7f9f2c529c76efc01da4b30271a66608da4728f9830ea17d29bc'
            web3 = Web3(Web3.HTTPProvider(rpc_url))

            if not web3.is_connected():
                return JsonResponse({'success': False, 'error': 'Failed to connect to blockchain node'}, status=500)

            def build_and_estimate_gas():
                token_contract = web3.eth.contract(address=Web3.to_checksum_address(token_contract_address), abi=ERC20_ABI)
                tx_data = token_contract.functions.transfer(receiver_address, int(amount)).build_transaction({
                    'from': sender_address,
                    'gas': 0,
                    'gasPrice': 0,
                })
                gas_estimate = web3.eth.estimate_gas(tx_data)
                gas_price = web3.eth.gas_price
                gas_fee_wei = gas_estimate * gas_price
                gas_fee_native = web3.from_wei(gas_fee_wei, 'ether')
                native_currency = fetch_native_currency(blockchain)
                return {
                    'gas_fee_wei': gas_fee_wei,
                    'gas_fee_native': float(gas_fee_native),
                    'native_currency': native_currency
                }

            result = retry_on_specific_error(build_and_estimate_gas)
            return JsonResponse({'success': True, **result})

        except Exception as e:
            print(f"Error: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

def crypto_chain_transfer(request):
    if request.method == 'POST':
        user_ip = get_client_ip(request)
        user_key = f"rate_limit_{user_ip}_calculate_chain_gas_price"

        if is_rate_limited(user_key):
            return JsonResponse({'success': False, 'error': 'Rate limit exceeded. Try again later.'}, status=429)
        try:
            data = json.loads(request.body.decode('utf-8'))
            sender_address = data.get('sender_address')
            private_key = data.get('private_key')
            receiver_address = data.get('receiver_address')
            amount = data.get('amount')
            chain_id = data.get('chain_id')
            blockchain = data.get('blockchain')
            calculated_gas_fee = data.get('calculated_gas_fee')

            rpc_url = f'https://rpc.ankr.com/{blockchain}/f7c0df84b43c7f9f2c529c76efc01da4b30271a66608da4728f9830ea17d29bc'
            web3 = Web3(Web3.HTTPProvider(rpc_url))

            if web3.is_connected():
                def build_and_send_transaction():
                    amount_in_wei = web3.to_wei(amount, 'ether')
                    nonce = web3.eth.get_transaction_count(sender_address)
                    transaction = {
                        'nonce': nonce,
                        'to': receiver_address,
                        'value': amount_in_wei,
                        'gas': 2000000,
                        'gasPrice': web3.eth.gas_price,
                        'chainId': int(chain_id)
                    }
                    gas_estimate = web3.eth.estimate_gas(transaction)
                    gas_fee_wei = gas_estimate * web3.eth.gas_price
                    if gas_fee_wei == calculated_gas_fee:
                        signed_tx = web3.eth.account.sign_transaction(transaction, private_key)
                        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
                        return web3.to_hex(tx_hash)
                    else:
                        raise Exception("gas fees do not match")

                tx_hash_hex = retry_on_specific_error(build_and_send_transaction)
                return JsonResponse({'success': True, 'tx_hash': tx_hash_hex})
            else:
                return JsonResponse({'success': False, 'error': 'Failed to connect to blockchain node'}, status=500)

        except Exception as e:
            print(f"Error: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

def crypto_token_transfer(request):
    if request.method == 'POST':
        user_ip = get_client_ip(request)
        user_key = f"rate_limit_{user_ip}_calculate_chain_gas_price"

        if is_rate_limited(user_key):
            return JsonResponse({'success': False, 'error': 'Rate limit exceeded. Try again later.'}, status=429)
        try:
            data = json.loads(request.body.decode('utf-8'))
            sender_address = data.get('sender_address')
            private_key = data.get('private_key')
            receiver_address = data.get('receiver_address')
            amount = data.get('amount')
            chain_id = data.get('chain_id')
            blockchain = data.get('blockchain')
            token_contract_address = data.get('token_contract_address')
            calculated_gas_fee = data.get('calculated_gas_fee')

            if not all([sender_address, private_key, receiver_address, amount, chain_id, blockchain, token_contract_address]):
                return JsonResponse({'success': False, 'error': 'Missing required fields'}, status=400)

            # Ensure addresses are valid and not zero address
            if sender_address.lower() == '0x0000000000000000000000000000000000000000' or receiver_address.lower() == '0x0000000000000000000000000000000000000000':
                return JsonResponse({'success': False, 'error': 'Invalid sender or receiver address'}, status=400)

            # Convert to checksum addresses
            sender_address = Web3.to_checksum_address(sender_address)
            receiver_address = Web3.to_checksum_address(receiver_address)
            token_contract_address = Web3.to_checksum_address(token_contract_address)

            rpc_url = f'https://rpc.ankr.com/{blockchain}/f7c0df84b43c7f9f2c529c76efc01da4b30271a66608da4728f9830ea17d29bc'
            web3 = Web3(Web3.HTTPProvider(rpc_url))

            if web3.is_connected():
                nonce = web3.eth.get_transaction_count(sender_address)
                token_contract = web3.eth.contract(address=token_contract_address, abi=ERC20_ABI)

                def build_and_send_transaction():
                    tx = token_contract.functions.transfer(
                        receiver_address,
                        int(amount)
                    ).build_transaction({
                        'chainId': int(chain_id),
                        'gas': 2000000,  # Provide a reasonable gas limit
                        'gasPrice': web3.eth.gas_price,
                        'nonce': nonce,
                        'from': sender_address
                    })
                    
                    tx_data = token_contract.functions.transfer(receiver_address, int(amount)).build_transaction({
                        'from': sender_address,
                        'gas': 0,
                        'gasPrice': 0,
                    })

                    gas_estimate = web3.eth.estimate_gas(tx_data)
                    gas_price = web3.eth.gas_price
                    gas_fee_wei = gas_estimate * gas_price

                    if gas_fee_wei == calculated_gas_fee:
                        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
                        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
                        return web3.to_hex(tx_hash)
                    else:
                        raise Exception("fees do not match")
                
                # Retry on error
                tx_hash_hex = retry_on_specific_error(build_and_send_transaction)
                
                return JsonResponse({'success': True, 'tx_hash': tx_hash_hex})
            else:
                return JsonResponse({'success': False, 'error': 'Failed to connect to blockchain node'}, status=500)

        except Exception as e:
            print(f"Error: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)