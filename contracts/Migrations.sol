pragma solidity ^0.5.0;

import { ENSRegistry } from "@ensdomains/ens/contracts/ENSRegistry.sol";
/* import "@ensdomains/ens/contracts/FIFSRegistrar.sol"; */
import { ReverseRegistrar } from "@ensdomains/ens/contracts/ReverseRegistrar.sol";
import { PublicResolver } from "@ensdomains/resolver/contracts/PublicResolver.sol";
import { BaseRegistrar, BaseRegistrarImplementation } from "@ensdomains/ethregistrar/contracts/BaseRegistrarImplementation.sol";
import { ETHRegistrarController, PriceOracle } from "@ensdomains/ethregistrar/contracts/ETHRegistrarController.sol";

contract DummyPriceOracle is PriceOracle {
  constructor() public {}
  /**
   * @dev Returns the price to register or renew a name.
   * @param name The name being registered or renewed.
   * @param expires When the name presently expires (0 if this is a new registration).
   * @param duration How long the name is being registered or extended for, in seconds.
   * @return The price of this renewal or registration, in wei.
   */
  function price(string calldata name, uint expires, uint duration) external view returns(uint) {
    return 200;
  }
}

// Construct a set of test ENS contracts.
contract TestDependencies {
  bytes32 constant TLD_LABEL = keccak256("eth");
  bytes32 constant RESOLVER_LABEL = keccak256("resolver");
  bytes32 constant REVERSE_REGISTRAR_LABEL = keccak256("reverse");
  bytes32 constant ADDR_LABEL = keccak256("addr");

  event AllAddresses(address ens,
                     address ethRegistrar,
                     address publicResolver,
                     address reverseRegistrar,
                     address controller);

  function namehash(bytes32 node, bytes32 label) public pure returns (bytes32) {
    return keccak256(abi.encodePacked(node, label));
  }

  constructor(ENSRegistry ens,
              BaseRegistrar ethRegistrar,
              PublicResolver publicResolver,
              ReverseRegistrar reverseRegistrar) public {
    // Set up the resolver
    bytes32 resolverNode = namehash(bytes32(0), RESOLVER_LABEL);
    bytes32 tldNode = namehash(bytes32(0), TLD_LABEL);

    /* ens.setSubnodeOwner(bytes32(0), RESOLVER_LABEL, address(this)); */

    /* ens.setResolver(resolverNode, address(publicResolver)); */
    /* publicResolver.setAddr(resolverNode, address(publicResolver)); */

    ens.setResolver(tldNode, address(publicResolver));
    publicResolver.setAddr(tldNode, address(publicResolver));

    // Create a ETH registrar for the TLD
    ens.setSubnodeOwner(bytes32(0), TLD_LABEL, address(ethRegistrar));

    DummyPriceOracle prices = new DummyPriceOracle();
    uint minCommitmentAge = 1;
    uint maxCommitmentAge = 3600;
    ETHRegistrarController controller = new ETHRegistrarController(ethRegistrar, PriceOracle(prices), minCommitmentAge, maxCommitmentAge);
    ethRegistrar.addController(address(controller));

    // Construct a new reverse registrar and point it at the public resolver

    // Set up the reverse registrar
    ens.setSubnodeOwner(bytes32(0), REVERSE_REGISTRAR_LABEL, address(this));
    ens.setSubnodeOwner(namehash(bytes32(0), REVERSE_REGISTRAR_LABEL), ADDR_LABEL, address(reverseRegistrar));

    emit AllAddresses(address(ens),
                      address(ethRegistrar),
                      address(publicResolver),
                      address(reverseRegistrar),
                      address(controller));
  }
}
