from web3 import Web3
import requests
from requests.adapters import Retry

RPC_OPTIMISM       = 'https://rpc.ankr.com/optimism/'
RPC_ARBITRUM       = 'https://arbitrum-one.publicnode.com'
RPC_CEPOLIA        = 'https://rpc.sepolia.org/'
RPC_SCROLL_SEPOLIA = 'https://sepolia-rpc.scroll.io'

number_of_thread = 1                                                 # Количество потоков

time_delay_min   = 20                                                # Минимальная и
time_delay_max   = 30                                                # Максимальная задержка между транзакциями

auto_chain       = True                                              # Авто выбор сети для merkly refuel в sepolia где больше баланса (Арбитрум, Оптимизм) True / False
chain_bridge     = 2                                                 # Ручной выбор сети, если auto_chain = False
                                                                     # 1 - Арбитрум, 2 - Оптимизм

sepolia_eth_min     = 0.08                                           # Минимальное и
sepolia_eth_max     = 0.1                                            # Максимальное количество ETH которое надо в Sepolia
sepolia_eth_decimal = 4                                              # Округление этой суммы (Количество знаков после запятой)

fees                = 0.009                                          # Сумма Fees, которая написана на сайте https://scroll.io/bridge. Лучше ставить немного больше

deposit_from_sepolia_to_scroll = 0.8                                 # Какую чать баланса депать в из Sepolia в SCROLL (0.9 - рекомендую)

value_swap_min     = 0.00001                                         # Минимальное и
value_swap_max     = 0.0001                                          # Максимальное количество ETH для свапа в uniswap
value_swap_decimal = 5                                               # Округление этой суммы (Количество знаков после запятой)

number_of_repetitions_min = 2                                        # Количество кругов (повторений купил - продал)
number_of_repetitions_max = 2                                        # Количество кругов (повторений купил - продал)

value_liquid_min     = 0.00001                                       # Минимальное и
value_liquid_max     = 0.0001                                        # Максимальное количество ETH для добавления ликвидности
value_liquid_decimal = 5                                             # Округление этой суммы (Количество знаков после запятой)

# End settings ------------------------------------------------------------------------------------------------------

retries = Retry(total=10, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
adapter = requests.adapters.HTTPAdapter(max_retries=retries)
session = requests.Session()
session.mount('http://', adapter)
session.mount('https://', adapter)
OPTIMISM_CHAIN = {'web3': Web3(Web3.HTTPProvider(RPC_OPTIMISM, request_kwargs={'timeout': 60}, session=session)),
                  'name': 'Optimism',
                  'scan': 'https://optimistic.etherscan.io/tx/',
                  'merkly': Web3.to_checksum_address('0xd7ba4057f43a7c4d4a34634b2a3151a60bf78f0d'),
                  }

session1 = requests.Session()
session1.mount('http://', adapter)
session1.mount('https://', adapter)
ARBITRUM_CHAIN = {'web3': Web3(Web3.HTTPProvider(RPC_ARBITRUM, request_kwargs={'timeout': 60}, session=session1)),
                  'name': 'Arbitrum',
                  'scan': 'https://arbiscan.io/tx/',
                  'merkly': Web3.to_checksum_address('0x4ae8cebccd7027820ba83188dfd73ccad0a92806'),
                  }

session2 = requests.Session()
session2.mount('http://', adapter)
session2.mount('https://', adapter)
SEPOLIA_CHAIN = {
    'web3': Web3(Web3.HTTPProvider(RPC_CEPOLIA, request_kwargs={'timeout': 60}, session=session2)),
    'name': 'Sepolia',
    'scan': 'https://sepolia.etherscan.io/tx/',
    'symbol': 'ETH',
    'scroll bridge': Web3.to_checksum_address('0x13FBE0D0e5552b8c9c4AE9e2435F38f37355998a'),
              }

session3 = requests.Session()
session3.mount('http://', adapter)
session3.mount('https://', adapter)
SCROLL_SEPOLIA_CHAIN = {
    'web3': Web3(Web3.HTTPProvider(RPC_SCROLL_SEPOLIA, request_kwargs={'timeout': 60}, session=session3)),
    'name': 'SCROLL_SEPOLIA',
    'scan': 'https://sepolia-blockscout.scroll.io/tx/',
    'symbol': 'ETH',
    'router': Web3.to_checksum_address('0x17AFD0263D6909Ba1F9a8EAC697f76532365Fb95'),
    'quoter': Web3.to_checksum_address("0xd5dd33650Ef1DC6D23069aEDC8EAE87b0D3619B2"),
    'eth': Web3.to_checksum_address("0x5300000000000000000000000000000000000004"),
    'gho': Web3.to_checksum_address("0xD9692f1748aFEe00FACE2da35242417dd05a8615"),
    'liquid': Web3.to_checksum_address('0xbbAd0e891922A8A4a7e9c39d4cc0559117016fec'),
              }
