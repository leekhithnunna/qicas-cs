// Only used to run a local node: `npx hardhat node` (chainId 31337, 20 unlocked accounts with 10000 ETH).
// Optional: copy ../contracts/CarbonScheduleMarket.sol into ./contracts and run `npx hardhat compile`
// to re-verify the artifact with the native compiler.
module.exports = {
  solidity: { version: "0.8.24", settings: { optimizer: { enabled: true, runs: 200 }, viaIR: true, evmVersion: "paris" } },
  networks: { hardhat: { blockGasLimit: 30000000 } }
};
