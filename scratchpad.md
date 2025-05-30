# Meeting notes

### 2025-05: DDoS for segments and data availability verification

> Meeting notes:
>
> - We can send the segment header and verify that it points to the right previous segment.
> - Segments are forming a change, by agreeing on a single segment header we can agree from
>   everything below.
> - Verify the history and see that this is the consistent view.
> - Regardless if the parent shard is verifying it, the algorithm should deal with rubbish being
>   sent up.
> - Can we minimise the chance of this happening to make this recovery less frequent.
> - This can lead to DDoS'ing through doing this. Use a probabilistic (data availability-like)
>   measure?
>
> Add a time window that allows to determine if the segment is available or not. Surface
> unavailability for the beacon chain. Votes for availability.
>
> Rely on the availablity for verification, use an optimistic approach for segments.
>
> DDoS'ing is only an issue with a 51% attack.

> TODO: Think about DDoS'ing in the beacon chain.

### 2025-05: Segment Proofs

> Meeting notes: We have all the information to check that the piece is part of the history, but not
> that is part of the global history.
>
> Segment root, and a prove that it is part of something bigger.
>
> I receive a piece I want to check that is part of the segment, and that the segment is part of the
> history.
>
> - Wherever we put this information I need to put the information for the global history proof.
>
> - Method that verifies the piece:
>   https://github.com/nazar-pc/abundance/blob/3bc565026e6a2222e892ccb3727503e79216b4db/subspace/crates/subspace-core-primitives/src/pieces.rs#L1007-L1021
>
> - When I update the global index I need to update also the history proof to create the piece.
>
> It is updated with the global_history_proof. It is added to the segment. Added to the header to
> the segment and not to the pieces so it shouldn't change the structure.

> Ideally you would only need to store the super segment proofs in order to get the segments. Shards
> should also store segment headers so that you can return them efficiently.. This late thing is an
> implementation detail not part of the consensus.

## Proving a block

- Every block created by a child shard is committed in the parent chain so it can be used to prove
  state and events happening in the shard without having to follow the entire chain.
- Every new shard block needs to include at least the following information:

```rust
struct BlockHeader {
	// The hash of the previous block in the shard
	prev_hash: Hash,
	// The hash of the last block in the beacon chain seen added to a segment
	// (blocks added to a segment for archiving can be assumed as having
	// a low probability of being reorged).
	beacon_block: Hash,
	// Solution for the block
	block_solution: Proof,
}
```

- What we want to proof is that a block belongs to the history of the child shard.
- And that the the block committed to the parent chain is consistent with the global history in the
  parent.
- We go from the global history in the beacon chain and proof that a block from a child shard is
  valid.
- You have a hierarchical tree of shards of with a beacon chain in the root, and e.g. a child of the
  beacon chain A, and a child of A, B.

> To generate proofs. From the beacon chain we can generate proofs. That the storage item is there.
> You can make a decision that something happened. The solution to spamming is the header. Can
> verify the consensus side. Header will be stored in a block. How exactly it would work? It can be
> in the state or it can be in the state.
>
> !!! Describe how the proofs are generated. Assume that the parent is who "audits" the children.
>
> Every time a block is created in a shard, the latest block in the beacon chain is referenced.
>
> Rules to point to blocks in the beacon chain that are deep enough to avoid having to trigger
> reorgs in child shards due to reorgs in the beacon chain
>
> Proofs of blocks are used to verify things in contracts, proofs of segments is for retrievability.

## Proving a piece of a segment from a super segment

> `super_segment_proof` that proofs that this is part of the super segment. The piece will actually
> include more segments.
>
> Record roots --> segment roots --> Generate proofs out of the trees from records and the root.
> ---> record --> Record proof and record root --> From all records you get a segment root.
>
> The pieces are incomplete until the segment root is committed in the beacon chain. Segment header
> needs to change because it is assigned by the beacon chain sequentially.
>
> Concept of pre-piece before being assigned.
>
> There is information that needs to flow down before the piece is generated.
>
> Q: The interesting proof here is that the piece is part of the global history.
>
> L2 segments are committed to L1, and L1 will verify them appropriately, and will batch all the
> commitments and submit to beacon chain that is can create a segment commitment out of this.
>
> --> Segment --> Segment proof and a segment root -->

---

## Shard blocks commitment and proof generation.

The goal of this issue is to surface the core data structures and mechanics of the process of
committing and verifying the history of a child shard to the upper levels of the hierarchy.

> @nazar-pc, I decided to start with block proofs instead of segment proofs (which I know were the
> ones currently blocking you), because I thought these ones are easier to describe, and that way I
> can use this issue as a _"test issue"_ to understand the level of detail and code-correctness v.s
> pseudocode that is useful for this. I also want to check how efficient are discussions over issues
> (and if I should migrate them to Zulip or ephimeral PRs).

### Submitting blocks to the parent

1. Assume the following information (at least) in the `BlockHeader` of a shard block:

```rust
struct BlockHeader{
	/// Hash of the block.
	hash: Hash
	/// Block number
	number: BlockNumber
	/// State root (can be considered redundant if tx_root is included)
	state_root: Hash
	/// Root of the Merkle tree of transactions included in the block.
	tx_root: Hash
	/// Hash of the parent block.
	parent_hash: Hash
	/// Block solution.
	solution: Proof
	/// Block number and hash of the beacon block referenced by this hash block.
	beacon_chain_ref: (BlockNumber, Hash)
}
```

2. Farmers submit in a transaction the `BlockHeader` for new blocks to the parent chain. Blocks are
   only accepted if:

   - Points to the right parent block.
   - References a valid beacon chain block.
   - It has an increasing block number (unless a fork has happened and can be clearly identified)
   - The solution is within the right solution range.

3. If the verification is successful, the following information is stored in the parent shard for
   each shard.

```rust
/// Data structure that is kept on-chain with some basic information about
/// the blocks from child shards that have been committed in the parent chain.
/// Map<ShardId, Map<BlockNumber of child block, (MMR_roots, BlockNumber of parent child where child block was submitted)>>
let shardBlocksMap = HashMap<ShardId, HashMap<BlockNumber, (MMR_roots, BlockNumber)>>
```

4. Additionally, nodes can maintain a local cache of the MMR proofs for the shard blocks they are
   following. This allows them to efficiently generate inclusion proofs for shard blocks and verify
   their consistency with the global history. Only nodes interested in the shard will keep this
   cache, reducing their need to repeatedly query the parent chain for proof data, improving
   performance and availability, and reducing network overhead.

```rust
/// Data structure that nodes can optionally keep (or generate from parent shard
/// transactions) storing a view of the child shards history MMR.
///
/// There are several ways in which we can represent this information efficiently
/// in node data stores:
/// - Storing diff proofs for each block.
/// - Storing the whole MMR
///
let shardHistoryMap = HashMap<ShardId, HashMap<BlockNumber, MRR_proof>
```

5. It is recommended that full nodes in child shards also represent their own history as the MMR
   that the parent chain is generating as a view of their history, as it would allow them to
   efficiently generate inclusion proofs (and proofs derived from this) for events happening in the
   shard.

6. The protocol is recursive, so immediate children from the beacon chain are also submitting their
   blocks to the beacon chain, and the beacon chain itself keeps a view of the state (the history
   MMR of the shard) for each of its child shards.

### Generating block proofs.

In order to generate proofs that a given a block from a child shard belongs to the history of the
shard and is consistent with the global history of the system, the following functions need to be
implemented _(consider this as Rust-like pseudocode, and do not expect correct and compilable
code)_:

Below you an find a set of functions that allow to generate from the parent chain an inclusion proof
that enabled the verification of the history proof. The state required to generate these proofs can
be retrieved from a nodes local cache (if it keeps a view of the MMR with the history of the shard,
either because it is following the shard, or because it follows its parent), or by requesting by an
honest node in these chains that have the information required.

The code also includes the verification functions that allow to verify the proofs, and the suggested
data structure for the proof.

> @nazar-pc, as pointed out above, I am not sure if this is the right level of detail to include in
> order to be helpful for you. Happy to dig deeper into the implementation of some of the
> under-defined functions below (like e.g. sharing their full signatures, etc.). I feel this may be
> more efficient due to my lack of context of the original code-base, but let me know what works
> best.

```rust

/// Proves that a block from a child shard is consistent with the global history of the system
struct BlkInHistoryProof {
	/// Proof with the MMR path proof that allows to verify that the block belongs to
	/// the history of the shard
	shard_blk_proof: Vec<Hash>
	/// Block in the parent including the shard block commitment
	/// that can be used to verify that the transaction with the submission was
	/// included in the block
	///
	/// NOTE: We may want to include as part of the proof already the BlkInHistoryProof
	/// for the parent block, so we can verify that the parent block is also part of the
	/// history of the system (or we can let the user to request it separately)
	blk_parent: BlockNumber
	/// Merkle tree proof that the transaction that commits the block in the parent chain
	/// is included in the block.
	/// For this proof we just need to include the tree path to the transaction in the block
	/// that can be verified against the root of the block given the transaction.
	///
	/// NOTE: This proof is only needed if the transactions of the parent block are not available,
	/// we can probably prove this easily if we have access to the full block from the parent chain.
	parent_tx_proof: Vec<Hash>
}

/// Generates an inclusion proof for the block in the child shard.
/// This functions retrieves the information from any local cache from the node including information
/// about the history in the child shard and/or interacts with the parent chain to collect the
/// information.
fn generate_shard_block_proof<T: BlockId>(&self, shardId: ShardId, blockId: T): Result<ShardBlockProof, Error> {
	// Get from the parent the MMR proof that the block was included in the parent chain.
	let (child_blk_roots, parent_block_num) = shardBlocksMap.get(shardId).get(child_blk.number);
	let shard_blk_proof = shardHistoryMap.get(shardId).get(child_blk.number);

	// Get the parent block that included the child block submission to generate additional information
	// for the proof
	let parent_blk = parent_chain.get_blk(parent_block_num);
	// Find the transaction in the block that committed the child block in the parent chain.
	let parent_tx_proof = for tx in parent_block.transactions.iter() {
			// Check if the transaction references the child block number and transaction root
			if tx.has_child_block(blockId) {
				return tx_proof = tx.get_proof(child_block_number, child_tx_root);
			}
		}

	// TODO: Consider including as part of the block proof the inclusion proof for the parent block also
	// (it can also be requested as an independent call to this function instead of having to include it
	// recursively)
	BlkInHistoryProof {
		shard_blk_proof: shard_blk_proof,
		blk_parent: parent_block_num,
		parent_tx_proof: parent_tx_proof,
	}
}


/// Verifies given a block from a child shard that the block belongs to the history of the shard
fn verify_shard_blk_proof(&self, shard_blk: Block, proof: BlkInHistoryProof) -> Result<(), Error> {
	// verify that the shard_blk_proof is consistent with the roots stored in the parent chain.
	let (child_blk_roots, parent_block_num) = shardBlocksMap.get(shardId).get(child_blk.number);
	proof.shard_blk_proof.verify(child_blk_roots)?;

	// verify that the reference to the beacon chain block is consistent with our current view of the beacon chain
	// (all nodes are following the beacon chain, so performing this check should be easy to make)
	beacon_chain.get_block(shard_blk.beacon_chain_ref)?;

	// Get the parent block that included the child block submission to verify that the child block was submitted successfully.
	let parent_blk = parent_chain.get_blk(proof.blk_parent);

	// verify that the parent block in itself is consistent with the global history in its own parent chain (the beacon chain)
	verify_shard_blk_proof(parent_blk, proof.shard_blk_proof)?;

	// verify that the transaction in the parent block that committed the child block is included in the corresponding
	// block in the parent
	verify_tx_proof(shard_blk, proof.parent_tx_proof, parent_blk)?;
}

```

## Shard segments submission to the beacon chain

The goal of this issue is to surface the core data structures and mechanics of the process of
committing segments to the global history in the beacon chain, and verifying that a piece of a
segment belongs to the global history in the beacon chain. shard to the upper levels of the
hierarchy.

### Submitting segments to the parent.

> Notes:
>
> - Check block_import.rs::block_import_verification
> - Check archiver.rs::archive_block
> - Check subspace-core-primitives/pieces.rs::Record.

1. As soon as a new segment has been created in a child shard, it is included in the next block and
   submitted to
