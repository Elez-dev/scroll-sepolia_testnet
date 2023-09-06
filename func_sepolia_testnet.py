import json as js
import time
from eth_abi import encode
from requests import ConnectionError
from web3.exceptions import TransactionNotFound
from settings import *

TIME_TRANSACTION = 300


def check_stargate(hash_, log):
    try:
        url_ = 'https://api-mainnet.layerzero-scan.com/tx/' + hash_
        with requests.Session() as s:
            s.mount('http://', adapter)
            s.mount('https://', adapter)
            res_ = js.loads(s.get(url_, timeout=600).text)
        log.info(res_['messages'])
        if res_['messages'] == []:
            return 1

        if res_['messages'][0]['status'] != 'DELIVERED':
            return 1
        else:
            return 0
    except:
        return 1


def get_start_chain(private_key, log, retry=0):
    try:
        web3_arb = ARBITRUM_CHAIN['web3']
        web3_opt = OPTIMISM_CHAIN['web3']
        account = web3_opt.eth.account.from_key(private_key)
        address_wallet = account.address
        balance_arb = web3_arb.eth.get_balance(address_wallet)
        balance_opt = web3_opt.eth.get_balance(address_wallet)
        if balance_arb > balance_opt:
            chain = ARBITRUM_CHAIN
        else:
            chain = OPTIMISM_CHAIN
        log.info(f'Стартовая сеть - {chain["name"]}\n')
        return chain
    except ConnectionError:
        log.info('Ошибка подключения к интернету или проблемы с РПЦ')
        time.sleep(120)
        if retry > 30:
            return 0
        retry += 1
        get_start_chain(private_key, log, retry)

    except Exception as error:
        if isinstance(error.args[0], dict):
            if 'execute this request' in error.args[0]['message']:
                log.info('Ошибка запроса на RPC')
        else:
            log.info(f'{error}\n')
        time.sleep(120)
        if retry > 30:
            return 0
        retry += 1
        get_start_chain(private_key, log, retry)


def get_gas_sepolia(private_key, chain, amount, log):
    web3 = chain['web3']
    account = web3.eth.account.from_key(private_key)
    address_wallet = account.address
    try:
        if amount > 0.1:
            amount = 0.1
        abi = js.load(open('./abi/sepolia_refuel.txt'))
        contract = web3.eth.contract(address=chain['merkly'], abi=abi)
        zro_payment_address = Web3.to_checksum_address('0x0000000000000000000000000000000000000000')
        amount_wei = web3.to_hex(encode(["uint"], [Web3.to_wei(amount, "ether")]))
        adapter_params = "0x00020000000000000000000000000000000000000000000000000000000000030d40" + amount_wei[2:] + address_wallet[2:]
        fees = contract.functions.estimateSendFee(161, zro_payment_address, adapter_params).call()
        dick = {
            'from': address_wallet,
            'value': fees[0],
            'nonce': web3.eth.get_transaction_count(address_wallet),
            'gasPrice': web3.eth.gas_price
        }
        contract_txn = contract.functions.bridgeGas(161, address_wallet, adapter_params).build_transaction(dick)
        signed_txn = web3.eth.account.sign_transaction(contract_txn, private_key=private_key)
        time.sleep(1)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        log.info('Отправил транзакцию')
        hash_ = web3.to_hex(tx_hash)
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=TIME_TRANSACTION, poll_latency=30)
        if tx_receipt.status == 1:
            log.info('Транзакция смайнилась успешно')
        else:
            log.info('Транзакция сфейлилась, пытаюсь еще раз')

        log.info(f'Merkly refuel to Sepolia || {chain["scan"]}{hash_}\n')
        time.sleep(40)
        while check_stargate(hash_, log):
            log.info('Бридж еще не закончился')
            time.sleep(100)
        log.info('Бридж закончился\n')
        return 1
    except TransactionNotFound:
        log.info('Транзакция не смайнилась за долгий промежуток времени, пытаюсь еще раз')
        return 0

    except ConnectionError:
        log.info('Ошибка подключения к интернету или проблемы с РПЦ')
        time.sleep(120)
        return 0

    except Exception as error:
        log.info('Произошла ошибка')
        if isinstance(error.args[0], str):
            if 'is not in the chain after' in error.args[0]:
                log.info('Транзакция не смайнилась за долгий промежуток времени. Пытаюсь еще раз')

            elif 'Too Many Requests for url' in error.args[0]:
                log.info('Очень много запросов на rpc')
                time.sleep(150)
            else:
                log.info(f'{error}\n')
        elif isinstance(error.args[0], dict):
            if 'insufficient funds' in error.args[0]['message']:
                log.info('Ошибка, скорее всего нехватает комсы')

            elif 'execute this request' in error.args[0]['message']:
                log.info('Ошибка запроса на RPC, пытаюсь еще раз')

            elif 'max fee per gas' in error.args[0]['message'] or 'gas required exceeds allowance' in error.args[0]['message']:
                log.info('Ошибка газа, пытаюсь еще раз')

            else:
                log.info(f'{error}\n')

        else:
            log.info(f'{error}\n')
        time.sleep(120)
        return 0


def check_status_bridge(tx_hash, log):
    url = 'https://sepolia-api-bridge.scroll.io/api/txsbyhashes'
    json = {
        'txs': [tx_hash]
    }
    try:
        with requests.Session() as s:
            s.mount('http://', adapter)
            s.mount('https://', adapter)
            res1 = s.post(url, json=json, timeout=60)
        json_data = js.loads(res1.text)

        if json_data['data']['result'][0]['finalizeTx']['blockNumber'] != 0:
            return 0
        else:
            return 1
    except Exception as error:
        log.info(error)
        return 1


def bridge_from_sepolia_to_scroll(private_key, log):
    web3 = SEPOLIA_CHAIN['web3']
    account = web3.eth.account.from_key(private_key)
    address_wallet = account.address
    try:
        balance_sepolia = web3.eth.get_balance(address_wallet)
        value = int(balance_sepolia * deposit_from_sepolia_to_scroll)
        log.info(f'Bridge from Sepolia to Scroll - {Web3.from_wei(value, "ether")} ETH')
        scroll_abi = js.load(open('./abi/Scroll.txt'))
        gas = 600_000
        gas_price = web3.eth.gas_price + Web3.to_wei(2, 'gwei')
        gas_cost = gas_price * gas
        value = value - gas_cost
        contract = web3.eth.contract(address=SEPOLIA_CHAIN['scroll bridge'], abi=scroll_abi)
        amount_out = int(value - Web3.to_wei(fees, 'ether'))
        if amount_out < 0:
            log.info(f'Сумма для bridge < 0, наверное очень большой Fees')
            return 0
        contract_txn = contract.functions.depositETH(amount_out, 168000).build_transaction(
            {
                'from': address_wallet,
                'value': value,
                'nonce': web3.eth.get_transaction_count(address_wallet),
                'gasPrice': web3.eth.gas_price,
            }
        )
        signed_txn = web3.eth.account.sign_transaction(contract_txn, private_key=private_key)
        time.sleep(1)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        log.info('Отправил транзакцию')
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=TIME_TRANSACTION, poll_latency=30)
        if tx_receipt.status == 1:
            log.info('Транзакция смайнилась успешно')
        else:
            log.info('Транзакция сфейлилась, пытаюсь еще раз')
            time.sleep(120)
            return 0

        log.info(f'Bridge from Sepolia to Scroll || {SEPOLIA_CHAIN["scan"]}{web3.to_hex(tx_hash)}\n')

        time.sleep(60)
        while check_status_bridge(Web3.to_hex(tx_hash), log):
            log.info('Бридж еще не закончился')
            time.sleep(100)
        log.info('Бридж закончился\n')
        return 1

    except TransactionNotFound:
        log.info('Транзакция не смайнилась за долгий промежуток времени, пытаюсь еще раз')
        time.sleep(120)
        return 0

    except ConnectionError:
        log.info('Ошибка подключения к интернету или проблемы с РПЦ')
        time.sleep(120)
        return 0

    except Exception as error:
        log.info('Произошла ошибка')
        if isinstance(error.args[0], str):
            if 'is not in the chain after' in error.args[0]:
                log.info('Транзакция не смайнилась за долгий промежуток времени. Пытаюсь еще раз')

            else:
                log.info(error)

        if isinstance(error.args[0], dict):
            if 'execute this request' in error.args[0]['message']:
                log.info('Ошибка запроса на RPC, пытаюсь еще раз')

            elif 'insufficient funds' in error.args[0]['message']:
                log.info('Ошибка, скорее всего нехватает комсы.')

            elif 'max fee per gas' in error.args[0]['message'] or 'gas required exceeds allowance' in error.args[0]['message']:
                log.info('Ошибка газа, пытаюсь еще раз')

            else:
                log.info(f'{error}\n')

        else:
            log.info(f'{error}\n')

        time.sleep(120)
        return 0


def swap_eth_for_token(private_key, value, log):
    web3 = SCROLL_SEPOLIA_CHAIN['web3']
    account = web3.eth.account.from_key(private_key)
    address_wallet = account.address
    try:
        value = Web3.to_wei(value, 'ether')
        balance = web3.eth.get_balance(address_wallet)
        gas = 500_000
        gas_cost = gas * web3.eth.gas_price
        if value > balance - gas_cost:
            value = int((balance - gas_cost) * 0.9)

        if value <= 0:
            return 'balance'

        quoter_abi = js.load(open('./abi/quoter.txt'))
        router_abi = js.load(open('./abi/router.txt'))
        quoter_contract = web3.eth.contract(address=SCROLL_SEPOLIA_CHAIN['quoter'], abi=quoter_abi)
        router_contract = web3.eth.contract(address=SCROLL_SEPOLIA_CHAIN['router'], abi=router_abi)

        quoter_data = quoter_contract.functions.quoteExactInputSingle((SCROLL_SEPOLIA_CHAIN['eth'],
                                                                       SCROLL_SEPOLIA_CHAIN['gho'],
                                                                       value, 500, 0)).call()

        min_amount_out = int(quoter_data[0] - (quoter_data[0] / 100))

        txn_data = router_contract.encodeABI(
            fn_name="exactInputSingle",
            args=[(
                SCROLL_SEPOLIA_CHAIN['eth'],
                SCROLL_SEPOLIA_CHAIN['gho'],
                500,
                address_wallet,
                value,
                min_amount_out,
                0
            )]
        )
        deadline = int(time.time()) + 10000
        contract_txn = router_contract.functions.multicall(deadline, [txn_data]).build_transaction(
            {
                'from': address_wallet,
                'nonce': web3.eth.get_transaction_count(address_wallet),
                'gasPrice': Web3.to_wei(1, 'gwei'),
                'value': value
            }
        )

        gas = contract_txn['gas']
        contract_txn.update({'gas': int(gas * 2)})

        signed_txn = web3.eth.account.sign_transaction(contract_txn, private_key=private_key)
        time.sleep(1)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        log.info('Отправил транзакцию')
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=600, poll_latency=30)
        if tx_receipt.status == 1:
            log.info('Транзакция смайнилась успешно')
        else:
            log.info('Транзакция сфейлилась, пытаюсь еще раз')
            time.sleep(120)
            return 0

        log.info(f'Swap {Web3.from_wei(value, "ether")} ETH -> {round(Web3.from_wei(min_amount_out, "ether"), 5)} GHO || {SCROLL_SEPOLIA_CHAIN["scan"]}{web3.to_hex(tx_hash)}\n')
        return 1

    except TransactionNotFound:
        log.info('Транзакция не смайнилась за долгий промежуток времени, пытаюсь еще раз')
        time.sleep(120)
        return 0

    except ConnectionError:
        log.info('Ошибка подключения к интернету или проблемы с РПЦ')
        time.sleep(120)
        return 0

    except Exception as error:
        log.info('Произошла ошибка')
        if isinstance(error.args[0], str):
            if 'is not in the chain after' in error.args[0]:
                log.info('Транзакция не смайнилась за долгий промежуток времени. Пытаюсь еще раз')

            else:
                log.info(error)

        if isinstance(error.args[0], dict):
            if 'execute this request' in error.args[0]['message']:
                log.info('Ошибка запроса на RPC, пытаюсь еще раз')

            elif 'insufficient funds' in error.args[0]['message']:
                log.info('Ошибка, скорее всего нехватает комсы.')
                return 'balance'

            elif 'max fee per gas' in error.args[0]['message'] or 'gas required exceeds allowance' in error.args[0]['message']:
                log.info('Ошибка газа, пытаюсь еще раз')

            else:
                log.info(f'{error}\n')

        else:
            log.info(f'{error}\n')
        time.sleep(120)
        return 0


def approve(private_key, chain, token_to_approve, address_to_approve, log, refuel_chain):
    web3 = chain['web3']
    account = web3.eth.account.from_key(private_key)
    address_wallet = account.address
    try:
        abi = js.load(open('./abi/Token.txt'))
        token_contract = web3.eth.contract(address=token_to_approve, abi=abi)
        allowance = token_contract.functions.allowance(address_wallet, address_to_approve).call()
        time.sleep(1)
        decimal = token_contract.functions.decimals().call()
        if allowance > 10000 * 10 ** decimal:
            return 1
        max_amount = 2 ** 256 - 1
        nonce = web3.eth.get_transaction_count(address_wallet)
        dick = {
            'from': address_wallet,
            'nonce': nonce,
            'gasPrice': Web3.to_wei(1, 'gwei'),
        }

        tx = token_contract.functions.approve(address_to_approve, max_amount).build_transaction(dick)

        gas = tx['gas']
        tx.update({'gas': int(gas * 2)})

        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        log.info('Отправил транзакцию')
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=TIME_TRANSACTION, poll_latency=30)
        if tx_receipt.status == 1:
            log.info('Транзакция смайнилась успешно')
        else:
            log.info('Транзакция сфейлилась, пытаюсь еще раз')
            time.sleep(120)
            return 0

        log.info(f'approve || {chain["scan"]}{web3.to_hex(tx_hash)}\n')
        return 1

    except TransactionNotFound:
        log.info('Транзакция не смайнилась за долгий промежуток времени, пытаюсь еще раз')
        time.sleep(120)
        return 0

    except ConnectionError:
        log.info('Ошибка подключения к интернету или проблемы с РПЦ')
        time.sleep(120)
        return 0

    except Exception as error:
        log.info(f'approve error')
        if isinstance(error.args[0], str):
            if 'is not in the chain after' in error.args[0]:
                log.info('Транзакция не смайнилась за долгий промежуток времени. Пытаюсь еще раз')

            else:
                log.info(error)

        elif isinstance(error.args[0], dict):
            if 'execute this request' in error.args[0]['message']:
                log.info('Ошибка запроса на RPC, пытаюсь еще раз')

            elif 'insufficient funds' in error.args[0]['message'] or 'gas required exceeds allowance' in error.args[0]['message']:
                if refuel_chain is None:
                    log.info('Ошибка, скорее всего нехватает комсы из-за того что газ вырос.')

                else:
                    log.info('Ошибка, скорее всего нехватает комсы')

            elif 'max fee per gas' in error.args[0]['message']:
                log.info('Ошибка газа, пытаюсь еще раз')

            else:
                log.info(error)

        else:
            log.info({error})
            log.info(f'Пытаюсь еще раз\n')
        time.sleep(120)
        return 0


def swap_token_for_eth(private_key, log):
    web3 = SCROLL_SEPOLIA_CHAIN['web3']
    account = web3.eth.account.from_key(private_key)
    address_wallet = account.address
    try:
        quoter_abi = js.load(open('./abi/quoter.txt'))
        router_abi = js.load(open('./abi/router.txt'))
        token_abi = js.load(open('./abi/Token.txt'))
        quoter_contract = web3.eth.contract(address=SCROLL_SEPOLIA_CHAIN['quoter'], abi=quoter_abi)
        router_contract = web3.eth.contract(address=SCROLL_SEPOLIA_CHAIN['router'], abi=router_abi)
        token_contract = web3.eth.contract(address=SCROLL_SEPOLIA_CHAIN['gho'], abi=token_abi)

        token_balance = token_contract.functions.balanceOf(address_wallet).call()

        quoter_data = quoter_contract.functions.quoteExactInputSingle((SCROLL_SEPOLIA_CHAIN['gho'],
                                                                       SCROLL_SEPOLIA_CHAIN['eth'],
                                                                       token_balance, 500, 0)).call()

        min_amount_out = int(quoter_data[0] - (quoter_data[0] / 100))

        txn_data = router_contract.encodeABI(
            fn_name="exactInputSingle",
            args=[(
                SCROLL_SEPOLIA_CHAIN['gho'],
                SCROLL_SEPOLIA_CHAIN['eth'],
                500,
                Web3.to_checksum_address('0x0000000000000000000000000000000000000002'),
                token_balance,
                min_amount_out,
                0
            )]
        )

        unwrap_data = router_contract.encodeABI(
            fn_name="unwrapWETH9",
            args=[
                min_amount_out,
                address_wallet
            ]
        )

        allowance = token_contract.functions.allowance(address_wallet, SCROLL_SEPOLIA_CHAIN['router']).call()
        if allowance < Web3.to_wei(1000000, 'ether'):
            log.info('Нужен аппрув, делаю')
            for _ in range(20):
                res_ = approve(private_key, SCROLL_SEPOLIA_CHAIN, SCROLL_SEPOLIA_CHAIN['gho'],
                               SCROLL_SEPOLIA_CHAIN['router'], log, None)
                if res_ == 1:
                    break
            time.sleep(15)

        deadline = int(time.time()) + 10000
        contract_txn = router_contract.functions.multicall(deadline, [txn_data, unwrap_data]).build_transaction(
            {
                'from': address_wallet,
                'nonce': web3.eth.get_transaction_count(address_wallet),
                'gasPrice': Web3.to_wei(1, 'gwei'),
            }
        )

        gas = contract_txn['gas']
        contract_txn.update({'gas': int(gas * 2)})

        signed_txn = web3.eth.account.sign_transaction(contract_txn, private_key=private_key)
        time.sleep(1)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        log.info('Отправил транзакцию')
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=600, poll_latency=30)
        if tx_receipt.status == 1:
            log.info('Транзакция смайнилась успешно')
        else:
            log.info('Транзакция сфейлилась, пытаюсь еще раз')
            time.sleep(120)
            return 0

        log.info(f'Swap {round(Web3.from_wei(token_balance, "ether"), 5)} GHO -> {round(Web3.from_wei(min_amount_out, "ether"), 5)} ETH || {SCROLL_SEPOLIA_CHAIN["scan"]}{web3.to_hex(tx_hash)}\n')
        return 1

    except TransactionNotFound:
        log.info('Транзакция не смайнилась за долгий промежуток времени, пытаюсь еще раз')
        time.sleep(120)
        return 0

    except ConnectionError:
        log.info('Ошибка подключения к интернету или проблемы с РПЦ')
        time.sleep(120)
        return 0

    except Exception as error:
        log.info('Произошла ошибка')
        if isinstance(error.args[0], str):
            if 'is not in the chain after' in error.args[0]:
                log.info('Транзакция не смайнилась за долгий промежуток времени. Пытаюсь еще раз')

            else:
                log.info(error)

        if isinstance(error.args[0], dict):
            if 'execute this request' in error.args[0]['message']:
                log.info('Ошибка запроса на RPC, пытаюсь еще раз')

            elif 'insufficient funds' in error.args[0]['message']:
                log.info('Ошибка, скорее всего нехватает комсы.')
                return 'balance'

            elif 'max fee per gas' in error.args[0]['message'] or 'gas required exceeds allowance' in error.args[0]['message']:
                log.info('Ошибка газа, пытаюсь еще раз')

            else:
                log.info(f'{error}\n')

        else:
            log.info(f'{error}\n')

        time.sleep(120)
        return 0


def add_liquidity(private_key, log):
    web3 = SCROLL_SEPOLIA_CHAIN['web3']
    account = web3.eth.account.from_key(private_key)
    address_wallet = account.address
    try:
        quoter_abi = js.load(open('./abi/quoter.txt'))
        liquid = js.load(open('./abi/liquid.txt'))
        token_abi = js.load(open('./abi/Token.txt'))
        quoter_contract = web3.eth.contract(address=SCROLL_SEPOLIA_CHAIN['quoter'], abi=quoter_abi)
        router_contract = web3.eth.contract(address=SCROLL_SEPOLIA_CHAIN['liquid'], abi=liquid)
        token_contract = web3.eth.contract(address=SCROLL_SEPOLIA_CHAIN['gho'], abi=token_abi)

        token_balance = token_contract.functions.balanceOf(address_wallet).call()

        quoter_data = quoter_contract.functions.quoteExactInputSingle((SCROLL_SEPOLIA_CHAIN['gho'],
                                                                       SCROLL_SEPOLIA_CHAIN['eth'],
                                                                       token_balance, 500, 0)).call()
        amount_out_eth     = quoter_data[0]
        min_amount_out_eth = int(quoter_data[0] - (quoter_data[0] / 100))
        min_amount_out_gho = int(token_balance - (token_balance / 100))

        allowance = token_contract.functions.allowance(address_wallet, SCROLL_SEPOLIA_CHAIN['liquid']).call()
        if allowance < Web3.to_wei(1000000, 'ether'):
            log.info('Нужен аппрув, делаю')
            for _ in range(20):
                res_ = approve(private_key, SCROLL_SEPOLIA_CHAIN, SCROLL_SEPOLIA_CHAIN['gho'],
                               SCROLL_SEPOLIA_CHAIN['liquid'], log, None)
                if res_ == 1:
                    break
            time.sleep(15)

        deadline = int(time.time()) + 10000

        txn_data = router_contract.encodeABI(
            fn_name="mint",
            args=[(
                SCROLL_SEPOLIA_CHAIN['eth'],
                SCROLL_SEPOLIA_CHAIN['gho'],
                500,
                -0xd89a0,
                0xd89a0,
                amount_out_eth,
                token_balance,
                min_amount_out_eth,
                min_amount_out_gho,
                address_wallet,
                deadline,
            )]
        )
        contract_txn = router_contract.functions.multicall([txn_data]).build_transaction(
            {
                'from': address_wallet,
                'nonce': web3.eth.get_transaction_count(address_wallet),
                'gasPrice': Web3.to_wei(1, 'gwei'),
                'value': amount_out_eth
            }
        )

        gas = contract_txn['gas']
        contract_txn.update({'gas': int(gas * 2)})

        signed_txn = web3.eth.account.sign_transaction(contract_txn, private_key=private_key)
        time.sleep(1)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        log.info('Отправил транзакцию')
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=TIME_TRANSACTION, poll_latency=30)
        if tx_receipt.status == 1:
            log.info('Транзакция смайнилась успешно')
        else:
            log.info('Транзакция сфейлилась, пытаюсь еще раз')
            time.sleep(120)
            return 0

        log.info(f'Add liquidity Uniswap || {SCROLL_SEPOLIA_CHAIN["scan"]}{web3.to_hex(tx_hash)}\n')
        return 1

    except TransactionNotFound:
        log.info('Транзакция не смайнилась за долгий промежуток времени, пытаюсь еще раз')
        time.sleep(120)
        return 0

    except ConnectionError:
        log.info('Ошибка подключения к интернету или проблемы с РПЦ')
        time.sleep(120)
        return 0

    except Exception as error:
        log.info('Произошла ошибка')
        if isinstance(error.args[0], str):
            if 'is not in the chain after' in error.args[0]:
                log.info('Транзакция не смайнилась за долгий промежуток времени. Пытаюсь еще раз')

            else:
                log.info(error)

        if isinstance(error.args[0], dict):
            if 'execute this request' in error.args[0]['message']:
                log.info('Ошибка запроса на RPC, пытаюсь еще раз')

            elif 'insufficient funds' in error.args[0]['message']:
                log.info('Ошибка, скорее всего нехватает комсы.')
                return 'balance'

            elif 'max fee per gas' in error.args[0]['message'] or 'gas required exceeds allowance' in error.args[0]['message']:
                log.info('Ошибка газа, пытаюсь еще раз')

            else:
                log.info(f'{error}\n')

        else:
            log.info(f'{error}\n')

        time.sleep(120)
        return 0

