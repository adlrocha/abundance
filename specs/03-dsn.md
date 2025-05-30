# Decentralised Storage Network (DSN) and Availability Sampling Protocol

The DSN is a critical component designed to ensure the permanent, load-balanced, and fault-tolerant
storage of blockchain history.

The DSN's multi-layered architecture---comprising the Archival Storage Layer (L1), Pieces Cache
Layer (L2), and Content Delivery Network (CDN, L3)---ensures scalability, efficiency, and
durability. Below, we detail how each layer contributes to the availability sampling process.

#### 1\. Archival Storage Layer (L1)

- L1 is the foundational layer for long-term storage, ensuring the durability of all blockchain
  data. Blocks and segments are erasure-coded into source and parity pieces (e.g., for a (2M, M)
  erasure code, 2M pieces are created, where any M can reconstruct the original data). These pieces
  are distributed across farmers based on their pledged storage capacity, using a pseudorandom
  selection process to ensure uniform replication.
- Farmers store these pieces in local plots, which do not require synchronization with the full
  blockchain history, reducing storage overhead. The replication factor is dynamically adjusted
  based on network conditions to maintain durability.
- L1 stores all encoded pieces that are targets for sampling. If a sampled chunk is not available in
  higher layers (L2 or L3), it can be retrieved from L1 by decoding the relevant pieces from a
  farmer's plot. This layer is critical for handling rare cases where cache misses occur, ensuring
  data availability even for older segments.

#### 2\. Pieces Cache Layer (L2)

- L2 is designed for near-instant retrieval of frequently accessed pieces, minimizing latency. Each
  farmer maintains a small cache (less than 1% of pledged storage) of unencoded pieces, selected
  based on their proximity to the farmer's peer ID using a distributed hash table (DHT). When new
  segments are archived, farmers automatically populate their L2 cache with relevant pieces.
- 1.  Nodes generate new segments during archiving, temporarily storing them in their cache.
  2.  Farmers receive segment index announcements from block headers and compute piece index hashes.
  3.  Based on hash proximity to their peer ID, farmers pull relevant pieces to their L2 cache.
  4.  If a piece cannot be retrieved to L2, farmers may attempt to decode it from neighboring pieces
      using erasure coding.
- During sampling, nodes first request chunks from the L2 cache, leveraging its low-latency access.
  This layer significantly speeds up the sampling process, especially for frequently accessed data,
  reducing the need for resource-intensive L1 retrievals.

#### 3\. Content Delivery Network (CDN) Layer (L3)

- L3 is an ultra-fast layer for retrieving recent or popular data, operated by a permissioned
  network of nodes. Farmers upload newly created pieces to the CDN, and nodes can retrieve them at
  speeds comparable to web2 services. It also facilitates rapid communication for sampling requests
  and responses.
- While primarily for recent data, L3 can accelerate retrieval of sampled chunks if they are part of
  recently archived segments. It enhances the efficiency of sampling rounds, especially for light
  nodes prioritizing recent shards.

### Integration with Availability Sampling Protocol

The availability sampling protocol, as described, involves selecting random chunks from encoded
segments and blocks, requesting them from the network, and verifying their availability. The DSN
supports this process through the following mechanisms:

##### 1\. Storage and Distribution of Encoded Data

- When a block or segment is created, it is erasure-coded and distributed across the DSN's L1 layer.
  This ensures that each piece is replicated across multiple farmers, minimizing the risk of data
  loss due to farmer unavailability or malicious behavior.
- The DSN's load-balancing and fault-tolerant design, using consistent hashing and DHT, ensures that
  pieces are evenly distributed, supporting scalable sampling across shards.

#### 2\. Retrieval of Sampled Chunks

- Nodes select a random share index iii (0 to totalshares-1total_shares - 1totals​hares-1) and chunk
  index jjj (0 to numchunkspershare-1num_chunks_per_share - 1numc​hunksp​ers​hare-1), then request
  the chunk and its witness (Merkle paths for intra-share and inter-share verification).
- **DSN Role**:
  - Requests are first directed to the L2 cache of farmers, leveraging DHT for efficient lookup.
  - If not found in L2, the chunk is retrieved from L1 by decoding from the farmer's plot, which may
    involve requesting neighboring pieces.
  - L3 (CDN) may be used for recent data, enhancing retrieval speed.
- **Efficiency**: The multi-layered approach ensures most requests are handled quickly, supporting
  multiple sampling rounds to build confidence (e.g., achieving 99% confidence with ~460 samples for
  a 1% missing fraction, as per Table 3 in the protocol).

#### 3\. Verification and Availability Checking

- Nodes verify retrieved chunks by reconstructing Merkle paths to compute commitments (e.g.,
  CblockC_blockCb​lock for blocks, segmentcommitmentsegment_commitmentsegmentc​ommitment for
  segments) and compare with trusted values from BlockInfoBlockInfoBlockInfo or
  SegmentInfoSegmentInfoSegmentInfo.
- **DSN Role**: The DSN ensures chunks are available for retrieval. If a chunk cannot be retrieved,
  it indicates potential unavailability, triggering unavailability reporting via the
  **Unavailability Report Topic**.

#### 4\. Handling Unavailability and Recovery

- **Unavailability Reporting**: If sampling detects unavailability (e.g., multiple failed
  retrievals), nodes report details (shard ID, block height, failed indices) to the network. Reports
  are signed, broadcast, and submitted to the beacon chain for verification over windows like
  SOFTUNAVAILABILITYWINDOWSOFT_UNAVAILABILITY_WINDOWSOFTU​NAVAILABILITYW​INDOW and
  HARDUNAVAILABILITYWINDOWHARD_UNAVAILABILITY_WINDOWHARDU​NAVAILABILITYW​INDOW.
- **DSN Role in Recovery**:
  - Nodes can request missing pieces from other farmers via the DSN.
  - Using erasure coding, the system can reconstruct data if at least MMM out of 2M2M2M shares are
    available (see Table 4: Recovery Scenarios).
  - If fewer than MMM shares are available, the block is flagged unrecoverable, escalating to
    consensus mechanisms (e.g., retransmission).

#### 5\. Broadcast Channels and Network Communication

- The DSN supports broadcast channels like the **Shard Sampling Topic** for requesting and reporting
  chunk availability, and the **Unavailability Report Topic** for global unavailability reports.
  These channels ensure nodes can leverage sampling information from others, enhancing efficiency.

#### Key DSN Features Supporting Availability Sampling

- **Erasure Coding**: Enables data reconstruction from partial shares, critical for handling farmer
  failures (e.g., requiring at least MMM out of 2M2M2M shares for recovery, as per Table 4).
- **Replication**: Ensures each piece is stored multiple times, dynamically adjusted based on
  network conditions.
- **Distributed Hash Table (DHT)**: Used in L2 for efficient piece location, supporting
  load-balanced retrieval.
- **Fault Tolerance**: Handles farmer churn without disrupting availability, using replication and
  erasure coding.
- **Scalability**: Scales with network growth, supporting increased sampling as more farmers join.

#### Implementation Considerations

For developers implementing the DSN in the context of availability sampling, consider the following:

- **Farmer Participation**: Farmers must implement L1 (archival storage), L2 (cache), and optionally
  L3 (CDN), responding to sampling requests efficiently.
- **Node Behavior**: Nodes must integrate with the DSN for chunk retrieval, prioritizing L2 and L3
  before L1, and handle unavailability reporting.
- **Network Communication**: Implement gossip protocols for broadcasting sampling requests and
  reports, ensuring scalability.
- **Security**: Ensure all retrievals are authenticated, using cryptographic proofs (e.g., Merkle
  paths) for verification.
- **Parameters**: Adjust replication factors, cache sizes, and sampling rounds (e.g.,
  k>ln⁡(1-p)ln⁡(1-f)k > \frac{\ln(1 - p)}{\ln(1 - f)}k>ln(1-f)ln(1-p)​) based on network conditions
  and desired confidence levels (see Table 3: Sampling Requirements).
