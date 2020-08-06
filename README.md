
## Run polyjuice

Please see: https://github.com/nervosnetwork/polyjuice/blob/develop/README.md

## Deploy ENS contracts

First install ens contracts and compile them

Install node first required version v10.22.0 (lts/dubnium)

``` bash
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
========================================================================
ENSRegistry                 : 0x4187580354c12b2534388a81010cadde5cda4691
PublicResolver              : 0x8c8100651809d68099fecdc7a879d3532135d907
BaseRegistrarImplementation : 0x15508a48d54fb116f0e25c281f129ccccc9590ad
ReverseRegistrar            : 0x8d63a7b76cb5eef99d1ea582378356be77319356
DummyPriceOracle            : 0xb31b367894bd9dbc1b2c4b99ed3f6150192365c3
Controller                  : 0x5ee8bc8188234b173a00da85400f061363f83da6
========================================================================
```

## Run polyjuice proxy server

polyjuice proxy server is for proxying web3 rpc request to ckb and polyjuice.

``` bash
python3 server.py <listen-port> <tmp-dir> <ckb-binary-path> <ckb-rpc-url> <polyjuice-rpc-url>
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
export REACT_APP_ENS_ADDRESS=0x4187580354c12b2534388a81010cadde5cda4691
export REACT_APP_LABELS='{"4f5b812789fc606be1b3b16908db13fc7a9adf7ca72641f84d75b47069d3d7f0":"eth"}'
# The graph-node listen address
export REACT_APP_GRAPH_NODE_URI=http://localhost:8545/graphql
```

Start the app:

``` bash
yarn start
```

Open http://localhost:3000 to see the page.
