### References

- Dilithium v2 video: https://www.youtube.com/watch?v=aHZ5LbFpfpw
- Roughgarden foundations of blockchains video: https://www.youtube.com/watch?v=8IwnXURUzUw
- Nazar's endgame for Abundance design:
  https://gist.github.com/nazar-pc/760505c5ad7d56c20b2c75c1484e672f
- Derivation of PoSpace:
  https://forum.autonomys.xyz/t/change-derivation-of-pospace-seed-and-hdd-compatible-exploit/4438?u=nazar-pc
- Qu.ai whitepapers: https://docs.qu.ai/learn/academic-resources/whitepapers
- Farmer equivocation:
  https://forum.autonomys.xyz/t/farmer-equivocation-is-problematic/3063?u=nazar-pc

### Scratchpad

- Decoupling Subspace's PoA to match the primitives above.
- Flesh out storage archival of sidechains and generation of blocks in the different chains.
- Then focus on the security model.

1. There is unbounded number of assets with unknown properties, pegs and firewall in a a way that
   they are in the paper are not applicable
2. ATMS is also not really a thing in a way they describe it due to known and unbounded set of
   participants One major difference that I see in the paper comparing to what I'd like to see is
   the failure mode of their side chain. They say that While I think given the number of shards
   expected, there should be a mechanism to catch and recover from such event. There are, of course,
   challenges with how to design such a mechanism such that it is actually secure and lightweight in
   case no misbehavior is happening. Something we discussed, but never implemented in Subspace, was
   a delay in block rewards. For example you produce a block and only get reward for it N blocks
   later. This can be used for additional verifications to be done by older block producer (with
   respect to potential misbehavior) before receiving reward. That way some block producer may
   indicate a potential issue and then over time we'll collect enough votes to figure out if it is
   true or not, all based on beacon chain level only, without the need to follow any chain in
   particular all the time

Refusing to provide a "vote" for or against misbehavior may mean they don't get a reward, to
incentivize them to participate in this mechanism.
https://abundance.zulipchat.com/#narrow/channel/495788-research/topic/Merkle-root.20based.20validity.20proofs/with/511893794https://abundance.zulipchat.com/#narrow/channel/495788-research/topic/Merkle-root.20based.20validity.20proofs/with/511893794

- Explain how this formalisation is really useful because it can be used to reason about the
  security of rollups, bridges, and in our case the different layers of our target consensus
  algorithm.
- Describe the how the PoW sidechain doesn't add much because it describes how to build sidechain
  communication between PoW sidechains by implementing a set of smart contracts in each chain that
  can verify NIPoPoW.

- Use of epochs and blocks for global synchrony between chains.
- Use of internal and external transaction pools. Let's have a look at how each of them match what
  we are trying to do: And you may be wondering now, how are you planning to use all of these for
  the design of our system? Inspired by the concepts above, For our design we need to come up with
  the basic primitives that will allow us to formalise the basic primitives.
- NIPoPoW to verify that an event (or a transaction) has happened in the source blockchain.
- Firewall requirement
- Merged staking or independent staking.
- Merge operation to the history of two chains.
- Direct observation or certified-based observation.
- Epochs and slots for the global synchronous model.
- Validity language (defines how to validate a block and transactions in the ledger).
- Use of an internal an external transaction pools (implicitly).
  - Cross-net and internat mempools.
  - System transactions that do not affect the ledger state but are validated? (SDN-like)
- Found the formalisation to reason about the security and operation of the system as "pegged
  layers".

- Went deeper into how Subspace works to match the primitives in the consensus into the theoretical
  framework of the PoS sidechains paper.
- The system operates globally as a single network, but it is divided into different layers that are
  pegged to each other.
- Block proposers in each sidechain and the assignment of farmers to the different sidechains is
  determined by PoSt.
- Segments are created from records from all shards.
- No cross-shards transactions, just basic atomic primitives to burn and mint tokens and state locks
  that can be coupled to deploy complex cross-shard operations.

### Notes on segment commitments and data availability post-meetings.

> The reason of the super segment commitment we can create hierarchy where we have only super
> commitments stored by light clients.

>

> All the segments committed in the parent? How can we have light clients to verify light clients.
> They need to have access to all commitments. All commitments stored in the parent shard would
> allow for light clients?

> TODO: Initially 2-10 shards. Over time the bandwidth of the user and storage capacity will
> increase. Maybe we surface all the segments commitments to the beacon chain and the parent creates
> super commitment (one) instead of multiple layers. 1M shards shouldn't be a problem.

## Meeting notes (2025-04-16)

- TODO: Q: Nazar: How does availability currently works in Subspace? Can we assume that archived
  pieces from deeper history are available and we should focus on sampling the newer history?

  - In terms of caching, the assumption is that farmers are pulling pieces.
  - The pieces we are plotting half are sampling from the past history and half from recent history.
  - Every time we produce a segment some segments for someone will expire and create new segment.
  - No number to ensure availability segments.
  - The shard participant doesn't need top keep the deepest history necessarily.
  - Hypothetically you can recreate the segment from the block.
  - If it is not in the cache:
    - Get the other pieces from the segment up to 128 and erasure decode.
    - Extracted from the plot. Random walk of plots trying in a few steps and discover someone for
      the piece.
      - Same thing erasure decode from the plot.
    - 99.9% right now you can hit the shard.

- DSN:
- Piece downloading protocol (have a look at docs).
- Farmers cache pieces.
- Use the DHT and assume by network identity, try to download those pieces.
- In Subspace single chain I see everything so I know what I need to cache.
- Immediately after the segment is created in the shard I can cache it.
- For the rest I need to figure out what to cache.

- Q: I guess we want to force all the farmers from a shard to store all the encoded blocks required
  for availability sampling?
- Do we want to incentivise data sampling in any way? Add some information in the beacon chain about
  the availability of the different shards with the threshold that that farmer currently sees (the
  block proposer).
- Idea: Random availability check forced to block proposers through the randomness beacon and the
  beacon chain.
- Also, farmers will be checking the availability as they build their plots.
- How does DSN currently works?
- Can we assume
