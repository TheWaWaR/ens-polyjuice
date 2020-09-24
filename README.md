
## Run polyjuice

Please see: https://github.com/nervosnetwork/polyjuice/blob/b8aa0a931351ee4b9ccfa3dfd9634e3bb48996a0/README.md

## Deploy [ENS](https://ens.domains/) contracts

First install ens contracts and compile them

Install node first. (required version v10.22.0 (lts/dubnium))

``` bash
git clone https://github.com/TheWaWaR/ens-polyjuice.git
npm install -g truffle
npm install
truffle compile
```

Install python dependencies

```
sudo pip3 install crypto flask-jsonrpc flask-cors
```

Then deploy the contracts

``` bash
python3 deploy.py <tmp-dir> <ckb-binary-path> <ckb-rpc-url> <polyjuice-rpc-url>
```
**NOTE**: We assume ckb binary path is located in ckb data directory.

Above command will print some information like this:
```
==================================================================
[EoA lock args]       : 0xc8328aabcd9b9e8e64fbc566c4385c3bdeb219d7
[EoA account address] : 0xbd1977237363b62856832eb9deb0bd0347e175af
========================================================================
ENSRegistry                 : 0xac440749c4a91085520008d5d5841133ff43c1cb
PublicResolver              : 0xd01e87623b149f42f51b056e1648283eeb5c9f88
BaseRegistrarImplementation : 0x69e557c3c3573ffe5e1d2a6e1f524942c666e6f5
ReverseRegistrar            : 0x3444628b06640271d12a7b0a2c332ef58fe3ba09
DummyPriceOracle            : 0xa08eb1bc88723a7609594e8bbc8d2149b9a322e5
Controller                  : 0xbbc7b577758e91a73494fe5a6dfc2f9ce934f522
========================================================================
```

## Run polyjuice proxy server

polyjuice proxy server is for proxying web3 rpc request to ckb and polyjuice.

``` bash
python3 server.py 8545 <tmp-dir> <ckb-binary-path> <ckb-rpc-url> <eoa-address> <polyjuice-rpc-url>
```

## Run GraphQL server

First run graph-node. Please see: https://thegraph.com/docs/quick-start#local-development

``` bash
git clone https://github.com/graphprotocol/graph-node/
cd graph-node/docker
./setup.sh
docker-compose up
```

Then register ENS Subgraph:
``` bash
git clone https://github.com/ensdomains/ens-subgraph.git
cd ens-subgraph
yarn install
yarn setup
```

## Run ENS manager app (web UI)

``` bash
git clone https://github.com/ensdomains/ens-app.git
cd ens-app
git checkout tags/v1.2.3
yarn install
```

Then we need import some environement variables to let the app connect to local service:
``` bash
export REACT_APP_STAGE=local
export REACT_APP_MIGRATION_COMPLETE=True
# ENSRegistry address
export REACT_APP_ENS_ADDRESS=0xac440749c4a91085520008d5d5841133ff43c1cb
export REACT_APP_LABELS='{"4f5b812789fc606be1b3b16908db13fc7a9adf7ca72641f84d75b47069d3d7f0":"eth"}'
# The graph-node listen address
export REACT_APP_GRAPH_NODE_URI=http://127.0.0.1:8000/subgraphs/name/graphprotocol/ens
```

Start the app:

``` bash
yarn start
```

Open http://localhost:3000 to see the page.
