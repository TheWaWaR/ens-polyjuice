#!/usr/bin/env python3
#coding: utf-8

import os
import sys
import subprocess
import json
from typing import Any, Dict, List, Union, NoReturn, Optional

from flask import Flask, request
from flask_jsonrpc import JSONRPC
from flask_jsonrpc.exceptions import JSONRPCError
from flask_cors import CORS
from deploy import call_contract, commit_tx, send_jsonrpc, SENDER1, SENDER1_PRIVKEY, eoa_accounts


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
jsonrpc = JSONRPC(app, '/', enable_web_browsable_api=True)

if len(sys.argv) < 6:
    print('USAGE:\n  python3 server.py 8545 <tmp-dir> <ckb-binary-path> <ckb-rpc-url> <eoa-address> <polyjuice-rpc-url> ')
    exit(-1)
target_dir = sys.argv[2]
ckb_bin_path = sys.argv[3]
ckb_rpc_url = sys.argv[4]
eoa_account = sys.argv[5]
polyjuice_rpc_url = sys.argv[6] if len(sys.argv) == 7 else "http://localhost:8214"

eoa_accounts[SENDER1] = [eoa_account]

ckb_dir = os.path.dirname(os.path.abspath(ckb_bin_path))
privkey1_path = os.path.join(target_dir, "{}.privkey".format(SENDER1))

tx_receipts = {}

if not os.path.exists(privkey1_path):
    with open(privkey1_path, 'w') as f:
        f.write(SENDER1_PRIVKEY)

@app.before_request
def before():
    # print('[method]: {}'.format(request.method))
    # print('[path]: {}'.format(request.path))
    print('[data]: {}'.format(request.data))


@app.after_request
def after(resp):
    print('[Response]: {}'.format(resp.data.decode('utf-8')))
    return resp


@jsonrpc.method('eth_getLogs')
def get_logs(filter: Dict) -> List:
    # {
    #     "fromBlock":"0x6341",
    #     "toBlock":"latest",
    #     "address":"0xce2951d57b56a928b75f577f0dd53bcf0843fdf6",
    #     "topics":[
    #         "0xce0457fe73731f824cc272376169235128c118b49d344817417c6d108d155e82",
    #         "0x93cdeb708b7545dc668eb9280176169d1c33cfd8ed6f04690a0bcc88a93fc4ae",
    #     ],
    # }
    from_block = int(filter['fromBlock'], 0)
    to_block = filter['toBlock']
    to_block = None if to_block == 'latest' else int(to_block, 0)
    address = filter['address']
    topics = filter['topics']
    if isinstance(topics[0], list):
        topics = topics[0]
    # {
    #   "logIndex": "0x1", // 1
    #   "blockNumber":"0x1b4", // 436
    #   "blockHash": "0x8216c5785ac562ff41e2dcfdf5785ac562ff41e2dcfdf829c5a142f1fccd7d",
    #   "transactionHash":  "0xdf829c5a142f1fccd7d8216c5785ac562ff41e2dcfdf5785ac562ff41e2dcf",
    #   "transactionIndex": "0x0", // 0
    #   "address": "0x16c5785ac562ff41e2dcfdf829c5a142f1fccd7d",
    #   "data":"0x0000000000000000000000000000000000000000000000000000000000000000",
    #   "topics": ["0x59ebeb90bc63057b6515673c3ecf9438e5058bca0f92585014eced636878c9a5"]
    # }
    logs = send_jsonrpc(
        polyjuice_rpc_url,
        'get_logs',
        [from_block, to_block, address, topics, None],
    )
    return [{
        'logIndex': '0x1',
        'blockNumber': hex(info['block_number']),
        'blockHash': send_jsonrpc(ckb_rpc_url, 'get_block_hash', [hex(info['block_number'])]),
        'transactionHash': '0x3333111111111111111111111111111111111111111111111111111111333333',
        'transactionIndex': hex(info['tx_index']),
        'address': info['log']['address'],
        'data': info['log']['data'],
        'topics': info['log']['topics'],
    } for info in logs]

@jsonrpc.method('eth_call')
def eth_call(program: Dict, tag: Union[int, str]) -> str:
    destination = program['to'].lower()
    data = program['data']
    eoa_account = eoa_accounts[SENDER1][0]
    return send_jsonrpc(polyjuice_rpc_url, 'static_call', [eoa_account, destination, data])['return_data']

@jsonrpc.method('eth_getCode')
def get_code(address: str, tag: Union[int, str]) -> str:
    address = address.lower()
    print(address, tag)
    if address == '0x0000000000000000000000000000000000000000':
        return '0x'
    else:
        return send_jsonrpc(polyjuice_rpc_url, 'get_code', [address])['code']

@jsonrpc.method('eth_blockNumber')
def tip_number() -> str:
    return send_jsonrpc(ckb_rpc_url, 'get_tip_block_number')

def make_eth_block(ckb_block):
    # "result": {
    #   "difficulty": "0x4ea3f27bc",
    #   "extraData": "0x476574682f4c5649562f76312e302e302f6c696e75782f676f312e342e32",
    #   "gasLimit": "0x1388",
    #   "gasUsed": "0x0",
    #   "hash": "0xdc0818cf78f21a8e70579cb46a43643f78291264dda342ae31049421c82d21ae",
    #   "logsBloom": "0x00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
    #   "miner": "0xbb7b8287f3f0a933474a79eae42cbca977791171",
    #   "mixHash": "0x4fffe9ae21f1c9e15207b1f472d5bbdd68c9595d461666602f2be20daf5e7843",
    #   "nonce": "0x689056015818adbe",
    #   "number": "0x1b4",
    #   "parentHash": "0xe99e022112df268087ea7eafaf4790497fd21dbeeb6bd7a1721df161a6657a54",
    #   "receiptsRoot": "0x56e81f171bcc55a6ff8345e692c0f86e5b48e01b996cadc001622fb5e363b421",
    #   "sha3Uncles": "0x1dcc4de8dec75d7aab85b567b6ccd41ad312451b948a7413f0a142fd40d49347",
    #   "size": "0x220",
    #   "stateRoot": "0xddc8b0234c2e0cad087c8b389aa7ef01f7d79b2570bccb77ce48648aa61c904d",
    #   "timestamp": "0x55ba467c",
    #   "totalDifficulty": "0x78ed983323d",
    #   "transactions": [
    #   ],
    #   "transactionsRoot": "0x56e81f171bcc55a6ff8345e692c0f86e5b48e01b996cadc001622fb5e363b421",
    #   "uncles": [
    #   ]
    # }

    # header:
    #   compact_target: 0x20010000
    #   dao: 0x182a95d5921fa12eebf62fa6f286230007eb70034b0000000040025e7011ff06
    #   epoch: 0x3e80005000000
    #   hash: 0x066e3314ad9056af1883c43cd6f634ca3074a3b1bbe4adabedb5e96634f81efe
    #   nonce: 0x7ff7eefe9134c73fda44d18119c8080f
    #   number: 0x5
    #   parent_hash: 0xebfd106232606fc008d282da1c09b03e30948c89f1a16ed924fb821ba7cb0334
    #   proposals_hash: 0x0000000000000000000000000000000000000000000000000000000000000000
    #   timestamp: 0x17393a79c78
    #   transactions_root: 0x6aac9ba76ca3ae47ed0528aebd6d3caa65226f340cab6f10955ccdf12ed24bbb
    #   uncles_hash: 0x0000000000000000000000000000000000000000000000000000000000000000
    #   version: 0x0
    header = ckb_block['header']
    return {
        "hash": header['hash'],
        'number': header['number'],
        'parentHash': header['parent_hash'],
        'timestamp': hex(int(int(header['timestamp'], 0) / 1000)),
        'difficulty': '0xff',
        "gasLimit": "0x1388",
        "gasUsed": "0x0",
        "size": "0x220",
        "extraData": "0x476574682f4c5649562f76312e302e302f6c696e75782f676f312e342e32",
        "miner": "0xbb7b8287f3f0a933474a79eae42cbca977791171",
        "transactionsRoot": "0x111111111111111111111111111111111111111111111111111111111111aaaa",
        "sha3Uncles": "0x111111111111111111111111111111111111111111111111111111111111bbbb",
        "stateRoot": "0x111111111111111111111111111111111111111111111111111111111111cccc",
        "receiptsRoot": "0x56e81f171bcc55a6ff8345e692c0f86e5b48e01b996cadc001622fb5e363b421",
        'transactions': [],
        'uncles': [],
    }

@jsonrpc.method('eth_getBlockByNumber')
def get_block_by_number(number: str, full_tx: bool) -> Dict:
    if number == 'latest':
        number = send_jsonrpc(ckb_rpc_url, 'get_tip_block_number')
    result = send_jsonrpc(ckb_rpc_url, 'get_block_by_number', [number])
    return make_eth_block(result)

@jsonrpc.method('eth_getBlockByHash')
def get_block_by_hash(block_hash: str, full_tx: bool) -> Dict:
    result = send_jsonrpc(ckb_rpc_url, 'get_block', [block_hash])
    return make_eth_block(result)

@jsonrpc.method('eth_estimateGas')
def estimate_gas(args: Dict) -> str:
    return hex(1)

@jsonrpc.method('eth_sendTransaction')
def send_transaction(tx: Dict) -> str:
    # {
    #     "from": "0xc8328aabcd9b9e8e64fbc566c4385c3bdeb219d7",
    #     "data": "0xf14fcbc8c60fbd965d0b23eef5aea591a101ede8911c60d31776b9ab524cd20c594f155d",
    #     "to": "0xC20E5Fa5A5D92915452bf27BeB7D06E7CeC75652",
    #     "gas": "0x1"
    # }
    sender = tx['from'].lower()
    contract_address = tx['to'].lower()
    input_data = tx['data'].lower()
    value = int(tx.get('value', '0x0'), base=16)
    receipt = call_contract(polyjuice_rpc_url, contract_address, input_data, sender=SENDER1, value=value)
    commit_tx(
        target_dir, ckb_bin_path, ckb_dir, ckb_rpc_url, privkey1_path,
        receipt,
        polyjuice_rpc_url,
        'call-{}-{}'.format(contract_address, input_data)[:60],
    )
    tx_hash = receipt['tx_hash']
    block_hash = send_jsonrpc(ckb_rpc_url, 'get_transaction', [tx_hash])['tx_status']['block_hash']
    tx_receipts[tx_hash] = {
        'receipt': receipt,
        'block_hash': block_hash,
        'header': send_jsonrpc(ckb_rpc_url, 'get_header', [block_hash]),
        'sender': sender,
        'contract_address': contract_address,
        'input_data': input_data,
    }
    return receipt['tx_hash']

@jsonrpc.method('eth_getTransactionByHash')
def get_tx_by_hash(tx_hash: str) -> Dict:
    info = tx_receipts[tx_hash]
    receipt = info['receipt']
    header = info['header']
    block_hash = info['block_hash']
    block_number = header['number']
    return {
        "blockHash": block_hash,
        "blockNumber": block_number,
        "from": info['sender'],
        "gas":"0xc350",
        "gasPrice":"0x4a817c800",
        "hash": tx_hash,
        "input": info['input_data'],
        "nonce":"0x15",
        "to": info['contract_address'],
        "transactionIndex":"0x41",
        "value":"0xf3dbb76162000",
        "v":"0x25",
        "r":"0x1b5e176d927f8e9ab405058b2d2457392da3e20f328b16ddabcebc33eaac5fea",
        "s":"0x4ba69724e8f69de52f0125ad8b3c5c2cef33019bac3249e2c0a2192766d1721c"
    }

@jsonrpc.method('eth_getTransactionReceipt')
def get_tx_receipt(tx_hash: str) -> Dict:
    info = tx_receipts[tx_hash]
    receipt = info['receipt']
    header = info['header']
    block_hash = info['block_hash']
    block_number = header['number']
    return {
        "transactionHash": tx_hash,
        "transactionIndex":  '0x1',
        "blockNumber": block_number,
        "blockHash": block_hash,
        "cumulativeGasUsed": '0x33bc',
        "gasUsed": '0x4dc',
        "contractAddress": receipt["entrance_contract"],
        "logs": [{
            'logIndex': '0x1',
            'blockNumber': block_number,
            'blockHash': block_hash,
            'transactionHash': tx_hash,
            'transactionIndex': '0x1',
            'address': log['address'],
            'data': log['data'],
            'topics': log['topics'],
        } for log in receipt['logs']],
        "logsBloom": "0x00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
        "status": '0x1',
    }

@jsonrpc.method('eth_accounts')
def accounts() -> List[str]:
    return [eoa_accounts[SENDER1][0]]

@jsonrpc.method('net_version')
def version() -> str:
    # private network
    return '103'


if __name__ == '__main__':
    port = int(sys.argv[1])
    print('[EoA lock args]: {}'.format(SENDER1))
    print('[EoA account address]: {}'.format(eoa_account))
    print('[polyjuice url]: {}'.format(polyjuice_rpc_url))
    app.run(host='0.0.0.0', port=port, debug=True, threaded=False, processes=1)
