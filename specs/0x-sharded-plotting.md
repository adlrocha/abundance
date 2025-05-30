# Sharded Plotting Specification

Sharded plotting is the protocol that orchestrates the process of selecting, retrieving, and
archiving pieces from the hsitory of all shards into a farmer's plot. Plotting is used to archive
the systems history, and it represents the sybil-resistant resource that governs the election of
block proposers in the farming process.

### Protocol parameters

- `K`: space parameter (memory hardness) for *proof-of-space*, currently 20
- `RECENT_SEGMENTS`: number of latest archived segments that are considered Recent History for the
  purposes of Plotting (currently 3)
- `RECENT_HISTORY_FRACTION`: fraction of recently archived pieces from the `RECENT_SEGMENTS` in each
  sector (currently 1/10)
- `MIN_SECTOR_LIFETIME`: minimum lifetime of a plotted sector, measured in archived segments,
  currently 4
- `global_history_size`: number of segments in the global history across all shards stored in the
  beacon chain.
- `NUM_PIECES` is 256: the number of pieces in an Archived History Segment after erasure coding
  (`NUM_RAW_RECORDS/ERASURE_CODING_RATE`). See [sharded archiving](./01-sharded-archiving.md) for
  more details on this.

### Pre-Plotting Initialization

- Reserve `<2%` of allocated disk space for proofs and auxiliary information.
- Create a plot of size `plot_size = allocated_plotting_space`, ensuring it is a multiple of
  `sector_size`.
- Generate a farmer identity: a key pair `(public_key, secret_key)` under a digital signature
  scheme.
- Derive `public_key_hash = hash(public_key)` as the farmer’s ID and network peer ID in the DHT.
- Compute `sector_count = plot_size / sector_size`.

The history size is now `total_global_segments`, representing the total number of segments in the
global history across all shards. ===

1.  Given the total allocated disk space for a farmer, reserve some space (<2%) for proofs and other
    auxiliary information.
2.  Create a single plot of `plot_size = allocated_plotting_space`. Sizes of farmer plots are
    independent from the size of the blockchain history, but must be a multiple of `sector_size`.
3.  Generate a farmer identity, that is a key pair `public_key, secret_key` under the digital
    signature scheme. These signing keys are independent from reward address of an entity (exactly
    as payout address in Bitcoin mining) described
    in [Block reward address](https://subspace.github.io/protocol-specs/docs/consensus/consensus_chain#block-reward-address).
4.  Derive an identifier `public_key_hash` as `hash(public_key)`. This farmer id will also serve as
    the basis for their single global network peer id in the DHT.
5.  Determine the `sector_count = plot_size / sector_size`.

### Verifiable Sector Construction (VSC)

Determine which pieces are to be downloaded for this sector:

> Hash with concatenation instead of keyed_hash

1.  **Derive Sector ID**: Index the sectors sequentially and for each sector
    derive `sector_id = keyed_hash(public_key_hash, sector_index || global_history_size || shard_id)`,
    where `sector_index` is the sector index in the plot, `global_history_size` is the current
    history size at the time of sector creation in the beacon chain, and `shard_id` the specific
    shard for which the space of this plot will be dedicated for farming.
2.  **Piece Selection**: For each sector, for each `piece_offset` in `0..max_pieces_in_sector`,
    derive the `piece_index` in global blockchain history this slot will contain, as follows:
    1.  At the start of the chain,
        if `global_history_size <= RECENT_SEGMENTS / RECENT_HISTORY_FRACTION` the pieces for this
        sector are selected uniformly
        as `piece_index = keyed_hash(piece_offset, sector_id) mod (global_history_size * NUM_PIECES)` for `piece_offset` in `0..max_pieces_in_sector`
    2.  Later, when history grows
        (`global_history_size > RECENT_SEGMENTS / RECENT_HISTORY_FRACTION`) to make sure recent
        archived history is plotted on farmer storage as soon as possible we
        select `RECENT_HISTORY_FRACTION` of pieces for each sector from the
        last `RECENT_SEGMENTS` archived segments.
    3.  For `piece_offset` in `0..max_pieces_in_sector * RECENT_HISTORY_FRACTION * 2`:
        1.  If `piece_offset` is odd, select a piece from recent history
            as `piece_index = keyed_hash(piece_offset, sector_id) mod (RECENT_SEGMENTS * NUM_PIECES) + ((global_history_size - RECENT_SEGMENTS) * NUM_PIECES)`
        2.  If `piece_offset` is even, select a piece uniformly from all history
            as `piece_index = keyed_hash(piece_offset, sector_id) mod (global_history_size * NUM_PIECES)`
    4.  The rest of the pieces for this sector are selected uniformly
        as `piece_index = keyed_hash(piece_offset, sector_id) mod (global_history_size * NUM_PIECES)` for `piece_offset` in `(2 * RECENT_HISTORY_FRACTION * max_pieces_in_sector)..max_pieces_in_sector`
3.  **Piece Retrieval and Verification**: 3. Retain the `global_history_size` count at the time of
    sector creation. This sector will expire at a point in the future as described
    in [Sector Expiration](#sector-expiration)
    1. Retrieve each piece from the DSN using
       `(shard_id, local_segment_index, piece_offset_within_segment)`.
    2. Verify each piece against the `segment_root` from the beacon chain’s `segment_roots[]` for
       the corresponding `global_segment_index`, using Merkle proofs to ensure integrity.
    3. For each synced sector, proceed to Plotting phase.

<!-- Scratchpad
 2. **Piece Selection**:

   - Define `threshold = RECENT_SEGMENTS / RECENT_HISTORY_FRACTION`.
   - If `total_global_segments <= threshold`:
     - For each `piece_offset` in `0..max_pieces_in_sector - 1`:
       - Compute
         `piece_index = keyed_hash(piece_offset, sector_id) mod (total_global_segments * NUM_PIECES)`.
   - Else:
     - Let `L = floor(max_pieces_in_sector * RECENT_HISTORY_FRACTION * 2)`.
     - For each `piece_offset` in `0..max_pieces_in_sector - 1`:
       - If `piece_offset < L` and `piece_offset % 2 == 1` (odd):
         - Compute
           `offset = keyed_hash(piece_offset, sector_id) mod (RECENT_SEGMENTS * NUM_PIECES)`.
         - Compute `recent_start = (total_global_segments - RECENT_SEGMENTS) * NUM_PIECES`.
         - Set `piece_index = offset + recent_start`.
       - Otherwise:
         - Compute
           `piece_index = keyed_hash(piece_offset, sector_id) mod (total_global_segments * NUM_PIECES)`.

3. **Mapping to Shard-Specific Indices**:

   - For each `piece_index`:
     - Compute `global_segment_index = piece_index // NUM_PIECES`.
     - Compute `piece_offset_within_segment = piece_index % NUM_PIECES`.
     - Query the beacon chain to map `global_segment_index` to `(shard_id, local_segment_index)`
       using the ordered list of included `SegmentInfo`.

4. **Piece Retrieval and Verification**:
   - Retrieve each piece from the DSN using
     `(shard_id, local_segment_index, piece_offset_within_segment)`.
   - Verify each piece against the `segment_root` from the beacon chain’s `segment_roots[]` for the
     corresponding `global_segment_index`, using Merkle proofs to ensure integrity. -->

### Plotting to Disk

For each piece in the sector:

1.  Extract the bundled record from the piece and retain
    the `record_witness` and `record_proof` alongside the plot.
2.  Split the extracted record into `FULL_BYTES`-sized `record_chunks`, which are guaranteed to
    contain values that fit into the scalar field.
3.  Erasure code the record with `extended_chunks = extend(record_chunks, ERASURE_CODING_RATE)`
4.  Derive an `evaluation_seed` from `sector_id` and `piece_offset` within this sector
    as `evaluation_seed = hash(sector_id || piece_offset)`
5.  Derive a Chia proof-of-space table `pos_table = generate(K, evaluation_seed)`
6.  Initialize `num_successfully_encoded_chunks = 0` to indicate how many chunks were encoded so
    far.
7.  Iterate through each `(s_bucket, chunk)` in `extended_chunks`:
    1.  Query the `pos_table` for a valid proof-of-space `proof_of_space` for this chunk
        as `find_proof(pos_table, s_bucket)`.
    2.  If it exists, encode the current chunk as `encode(chunk, hash(proof_of_space))` and
        increase `num_successfully_encoded_chunks` by 1. Otherwise, continue to the next chunk.
    3.  Place the encoded chunk into a corresponding s-bucket for given index `s_bucket` and set
        corresponding bit in the `encoded_chunks_used` bitfield to `1`.
8.  If `num_successfully_encoded_chunks >= NUM_CHUNKS` all chunks were encoded successfully, take
    the necessary `NUM_CHUNKS` and proceed to the next record.
9.  Else, if `num_successfully_encoded_chunks < NUM_CHUNKS`, select extra chunks to store at the end
    after encoded chunks:
    1.  Compute `num_unproven = NUM_CHUNKS - num_successfully_encoded_chunks`
    2.  Save as `extra_chunks` the first `num_unproven` chunks of the source record corresponding to
        the indices where `encoded_chunks_used` is not set.
10. Once all records are encoded, write the sector to disk, one s-bucket at time in order of the
    index, each followed by `encoded_chunks_used` bitfield corresponding to selected chunks.
11. The final plotted sector consists of `max_pieces_in_sector` many `encoded_chunks_used` bitfields
    of size `NUM_S_BUCKETS` each, `NUM_S_BUCKETS` s-buckets and roots and proofs of pieces in this
    sector.

Each `encoded_chunks_used` indicator vector has bit set to `1` at places corresponding to the record
positions whose chunks are encoded in this s-bucket and are eligible for farming.

### Sector Expiration

After `MIN_SECTOR_LIFETIME` segments were archived (since sector creation), the farmer should check
whether the sector have expired and can no longer be farmed based on the "age" (history size at
plotting) of each sector. For each sector `sector_id` and `history_size` when this sector was
plotted:

1.  When current history size of the chain
    reaches `sector_expiration_check_history_size = history_size + MIN_SECTOR_LIFETIME` farmer
    should check when to expire this sector based on corresponding `segment_proof` of last archived
    segment.
2.  Compute `sector_max_lifetime = MIN_SECTOR_LIFETIME + 4 * global_history_size`. With this
    limitation on sector lifetime, a sector with expire with probability ~50% by the time history
    doubles since it's initial plotting point and is guaranteed to expire by the time history
    doubles again.
3.  Compute `expiration_history_size = hash(sector_id || segment_proof) mod (sector_max_lifetime - sector_expiration_check_history_size) + sector_expiration_check_history_size`
4.  When the current history size reaches `expiration_history_size`, expire this sector.
5.  Replot the sector for new history size as described in [Plotting](#plotting-to-disk).
