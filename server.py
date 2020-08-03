#!/usr/bin/env python3
#coding: utf-8

import sys
import subprocess
import json
from typing import Any, Dict, List, Union, NoReturn, Optional

from flask import Flask, request
from flask_jsonrpc import JSONRPC
from flask_jsonrpc.exceptions import JSONRPCError
from flask_cors import CORS

sender = '0xc8328aabcd9b9e8e64fbc566c4385c3bdeb219d7'

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
jsonrpc = JSONRPC(app, '/', enable_web_browsable_api=True)
polyjuice_rpc_url = sys.argv[2]
ckb_rpc_url = sys.argv[3]

def send_jsonrpc(url, method, params=[]):
    payload = {
        "id": 0,
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
    }
    cmd = "curl -s -H 'content-type: application/json' -d '{}' {}".format(json.dumps(payload), url)
    output = subprocess.check_output(cmd, shell=True).strip().decode("utf-8")
    resp = json.loads(output)
    print('[Polyjuice request]: method={}, params={}'.format(method, params))
    print('[Polyjuice response]: {}'.format(resp))
    if "error" in resp:
        error = resp["error"]
        raise JSONRPCError(message=error['message'], code=error['code'], status_code=400)
    return resp["result"]

@app.before_request
def before():
    print('[method]: {}'.format(request.method))
    print('[path]: {}'.format(request.path))
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
        [from_block, to_block, filter['address'], filter['topics'], None],
    )
    return [{
        'logIndex': '0x1',
        'blockNumber': hex(info['block_number']),
        'blockHash': '0x11111111111111111111111111111111111111111111111111111111111111',
        'transactionHash': '0x11111111111111111111111111111111111111111111111111111111111111',
        'transactionIndex': hex(info['tx_index']),
        'address': info['log']['address'],
        'data': info['log']['data'],
        'topics': info['log']['topics'],
    } for info in logs]

@jsonrpc.method('eth_call')
def call(program: Dict, tag: Union[int, str]) -> str:
    destination = program['to'].lower()
    data = program['data']
    return send_jsonrpc(polyjuice_rpc_url, 'static_call', [sender, destination, data])['return_data']

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

@jsonrpc.method('eth_getBlockByNumber')
def get_block_by_number(number: str, full_tx: bool) -> Dict:
    #     "result": {
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

    result = send_jsonrpc(ckb_rpc_url, 'get_block_by_number', [number])
    header = result['header']
    return {
        'difficulty': '0xff',
        'number': header['number'],
        'timestamp': hex(int(int(header['timestamp'], 0) / 1000)),
        'transactions': [],
        "transactionsRoot": "0x56e81f171bcc55a6ff8345e692c0f86e5b48e01b996cadc001622fb5e363b421",
        'uncles': [],
    }

@jsonrpc.method('eth_accounts')
def accounts() -> List[str]:
    return ['0xc8328aabcd9b9e8e64fbc566c4385c3bdeb219d7']

@jsonrpc.method('net_version')
def version() -> str:
    return '3'


if __name__ == '__main__':
    port = int(sys.argv[1])
    print('[polyjuice url]: {}'.format(polyjuice_rpc_url))
    app.run(host='0.0.0.0', port=port, debug=True)
