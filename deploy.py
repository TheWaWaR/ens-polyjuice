#/usr/bin/env python3
#coding: utf-8

import json
import sys
import os
import subprocess
import time
from binascii import hexlify
from namehash import namehash, sha3

SENDER1 = "0xc8328aabcd9b9e8e64fbc566c4385c3bdeb219d7"
SENDER1_PRIVKEY = "d00c06bfd800d27397002dca6fb0993d5ba6399b4238b2f29ee9deb97593d2bc"
target_dir = sys.argv[1]
ckb_bin_path = sys.argv[2]
ckb_rpc_url = sys.argv[3]
polyjuice_rpc_url = sys.argv[4] if len(sys.argv) == 5 else "http://localhost:8214"

ckb_dir = os.path.dirname(os.path.abspath(ckb_bin_path))
privkey1_path = os.path.join(target_dir, "{}.privkey".format(SENDER1))
os.environ["API_URL"] = ckb_rpc_url

if not os.path.exists(privkey1_path):
    with open(privkey1_path, 'w') as f:
        f.write(SENDER1_PRIVKEY)


def send_jsonrpc(method, params=[]):
    payload = {
        "id": 0,
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
    }
    cmd = "curl -s -H 'content-type: application/json' -d '{}' {}".format(json.dumps(payload), polyjuice_rpc_url)
    output = subprocess.check_output(cmd, shell=True).strip().decode("utf-8")
    resp = json.loads(output)
    if "error" in resp:
        print("JSONRPC ERROR: {}".format(resp["error"]))
        exit(-1)
    return resp["result"]

def create_contract(binary, constructor_args="", sender=SENDER1):
    print("[create contract]:")
    print("  sender = {}".format(sender))
    print("  binary = 0x{}".format(binary))
    print("    args = 0x{}".format(constructor_args))
    result = send_jsonrpc("create", [sender, "0x{}{}".format(binary, constructor_args)])
    print("  >> created address = {}".format(result["entrance_contract"]))
    return result

def call_contract(contract_address, args, is_static=False, sender=SENDER1):
    method = "static_call" if is_static else "call"
    print("[{} contract]:".format(method))
    print("   sender = {}".format(sender))
    print("  address = {}".format(contract_address))
    print("     args = {}".format(args))
    return send_jsonrpc(method, [sender, contract_address, args])

def mine_blocks(n=5):
    run_cmd("{} miner -C {} -l {}".format(ckb_bin_path, ckb_dir, n))
    time.sleep(0.5)

def run_cmd(cmd, print_output=True):
    print("[RUN]: {}".format(cmd))
    output = subprocess.check_output(cmd, shell=True, env=os.environ).strip().decode("utf-8")
    if print_output:
        print("[Output]: {}".format(output))
    return output

def commit_tx(result, action_name, privkey_path=privkey1_path):
    result_path = os.path.join(target_dir, "{}.json".format(action_name))
    with open(result_path, "w") as f:
        json.dump(result, f, indent=4)
    tx_path = os.path.join(target_dir, "{}-tx.json".format(action_name))
    tx_raw_path = os.path.join(target_dir, "{}-raw-tx.json".format(action_name))
    # tx_moack_path = os.path.join(target_dir, "{}-mock-tx.json".format(action_name))
    run_cmd("polyjuice sign-tx --url {} -k {} -t {} -o {}".format(ckb_rpc_url, privkey_path, result_path, tx_path))
    run_cmd("cat {} | jq .transaction > {}".format(tx_path, tx_raw_path))
    # run_cmd("ckb-cli mock-tx dump --tx-file {} --output-file {}".format(tx_raw_path, tx_moack_path))
    for retry in range(3):
        tx_hash = run_cmd("ckb-cli tx send --tx-file {} --skip-check".format(tx_path)).strip()
        mine_blocks()
        tx_content = run_cmd("ckb-cli rpc get_transaction --hash {}".format(tx_hash), print_output=False)
        if tx_content.find(tx_hash) > -1:
            print("Transaction sent: {}".format(tx_hash))
            break;
        print("Retry send transaction: {}".format(retry))

def get_code(path):
    with open(path) as f:
        data = json.load(f)
        return data['bytecode'][2:]

def addr_to_arg(addr):
    return "000000000000000000000000{}".format(addr[2:])

def gen_node(name):
    return hexlify(namehash(name)).decode('utf-8')

def gen_label(name):
    return hexlify(sha3(name)).decode('utf-8')


def call(addr, fn_name, args, name):
    args = ''.join(['0x', fn_name, *args])
    result = call_contract(addr, args)
    commit_tx(result, 'call-{}-{}'.format(name, args)[:45])

def main():
    tld_label = gen_label(b'eth')
    resolver_label = gen_label(b'resolver')
    reverse_label = gen_label(b'reverse')
    addr_label = gen_label(b'addr')

    tld_node = gen_node(b'eth')
    resolver_node = gen_node(b'resolver')
    reverse_node = gen_node(b'reverse')

    ens = create_contract(get_code('build/contracts/ENSRegistry.json'))
    commit_tx(ens, 'create-ENSRegistry')
    ens_addr = ens['entrance_contract'];

    ens_addr_arg = addr_to_arg(ens_addr)
    public_resolver = create_contract(
        get_code('build/contracts/PublicResolver.json'),
        constructor_args=ens_addr_arg,
    )
    commit_tx(public_resolver, 'create-PublicResolver')
    public_resolver_addr = public_resolver['entrance_contract'];

    constructor_args = ens_addr_arg + tld_node
    eth_registrar = create_contract(
        get_code('build/contracts/BaseRegistrarImplementation.json'),
        constructor_args=constructor_args,
    )
    commit_tx(eth_registrar, 'create-BaseRegistrarImplementation')
    eth_registrar_addr = eth_registrar['entrance_contract'];

    constructor_args = ens_addr_arg + addr_to_arg(public_resolver_addr)
    reverse_registrar = create_contract(
        get_code('build/contracts/ReverseRegistrar.json'),
        constructor_args=constructor_args,
    )
    reverse_registrar_addr = reverse_registrar['entrance_contract']
    commit_tx(reverse_registrar, 'create-ReverseRegistrar')

    fn_set_subnode_owner = '06ab5923'
    fn_set_resolver = '1896f70a'
    fn_set_addr = 'd5fa2b00'
    fn_add_controller = 'a7fc7a07'
    zero_node = '0000000000000000000000000000000000000000000000000000000000000000'

    account0 = SENDER1
    ## Setup Resolver
    for (label, node) in [(resolver_label, resolver_node), (tld_label, tld_node)]:
        call(
            ens_addr,
            fn_set_subnode_owner,
            [zero_node, label, addr_to_arg(account0)],
            'setSubnodeOwner',
        )
        call(
            ens_addr,
            fn_set_resolver,
            [node, addr_to_arg(public_resolver_addr)],
            'setResolver',
        )
        call(
            public_resolver_addr,
            fn_set_addr,
            [node, addr_to_arg(public_resolver_addr)],
            'setAddr',
        )
    ## Setup Registrar
    call(
        ens_addr,
        fn_set_subnode_owner,
        [zero_node, tld_label, addr_to_arg(eth_registrar_addr)],
        'setSubnodeOwner',
    )
    ## Setup ReverseRegistrar
    call(
        ens_addr,
        fn_set_subnode_owner,
        [zero_node, reverse_label, addr_to_arg(account0)],
        'setSubnodeOwner',
    )
    call(
        ens_addr,
        fn_set_subnode_owner,
        [reverse_node, addr_label, addr_to_arg(reverse_registrar_addr)],
        'setSubnodeOwner',
    )
    ## Setup Controller
    price_oracle = create_contract(get_code('build/contracts/DummyPriceOracle.json'))
    price_oracle_addr = price_oracle['entrance_contract']
    commit_tx(price_oracle, 'create-DummyPriceOracle')

    constructor_args = ''.join([
        addr_to_arg(eth_registrar_addr),
        addr_to_arg(price_oracle_addr),
        '0000000000000000000000000000000000000000000000000000000000000001',
        '0000000000000000000000000000000000000000000000000000000000000e10',
    ])
    controller = create_contract(
        get_code('build/contracts/ETHRegistrarController.json'),
        constructor_args = constructor_args,
    )
    controller_addr = controller['entrance_contract']
    commit_tx(controller, 'create-Controller')

    call(
        eth_registrar_addr,
        fn_add_controller,
        [addr_to_arg(controller_addr)],
        'addController',
    )

    print('========================================')
    print('ENSRegistry: {}'.format(ens_addr))
    print('PublicResolver: {}'.format(public_resolver_addr))
    print('BaseRegistrarImplementation: {}'.format(eth_registrar_addr))
    print('ReverseRegistrar: {}'.format(reverse_registrar_addr))
    print('DummyPriceOracle: {}'.format(price_oracle_addr))
    print('Controller: {}'.format(controller_addr))
    print('========================================')

if __name__ == '__main__':
    main()
