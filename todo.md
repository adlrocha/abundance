- [ ] Block proofs re-write.
  - Re-orgs / sync / impact of new block header
- [ ] Segment re-writes
  - Segment submission.
  - Super segments.
- [ ] Shard membership and farming.
- [ ] Data availability

-=======--====

- [ ] ZODA (Zero-Overhead Data Availability):
      https://abundance.zulipchat.com/#narrow/channel/495788-research/topic/ZODA.3A.20Zero-Overhead.20Data.20Availability/with/518435332
- [ ] Proof-of-stake longest chain protocols: SEcurity v.s. predictability:
      https://arxiv.org/abs/1910.02218
- [ ] Add to the parking lot:

  > I think the whole light client situation should be revisited. With a different storage model and
  > contracts that are closer to pure functions than to apps,

- [ ] Add to the parking lot

  > Consider the use of an independent PoT chain that does not depend on the beacon chain as a
  > source of entropy and is more efficient to verify and generate than the use of AES. Here's the
  > cryptography behind drand: https://docs.drand.love/docs/cryptography/

- [ ] Change the README of the spec to explain that I will start adding only the specs for things
      that are not implemented and that are under design, and that otherwise we are only going to
      point to the parts of the code that are already implemented. The code is the source of truth
      and is the way that we can avoid the code and the spec from being out of sync.

> https://abundance.zulipchat.com/#narrow/channel/495788-research/topic/Light.20client/near/517250894
> Actually I think things might be a bit simpler than I originally expected. First observation is
> that I think it may not be necessary to have external (to the blockchain) light client for
> arbitrary shard. It should be sufficient, at least for many use cases, to have a light client of
> the beacon chain only. Anything that is confirmed by the beacon chain will then be provable from
> it, hence light clients of individual shards should not be (strictly speaking) necessary. Though
> there might be use cases where we'll still need to retrieve information quicker. Second
> observation is that to do complete verification from genesis then it might be necessary to run
> both beacon chain and shard chain in parallel. However, if beacon chain is already synced, then
> shard chain can be bootstrapped from the last confirmed block of the shard, bypassing the whole
> DSN sync and deep history verification challenges.

I'm not sure we can have guarantees about all shards making progress more broadly, but if we can
then we can also establish upper bound on the amount of data beacon chain needs to retain to be able
to sync any shard. Something to explore.

Regarding the verification of consensus information:

> TODO: The way I imagined verification, none of this will ever need to be retrieved for
> verification. Super segment roots and beacon chain block headers should be the things against
> which proofs are built and fully verifiable, just like in Subspace the pieces are fully verifiable
> against segment roots without access to anything else.

# Meeting 2025-05-14

1. Discuss `BlockHeader`:
   https://github.com/nazar-pc/abundance/compare/main...block-layout#diff-f0ea9d8b207164fd2fa89ea59ca48f52bf2dc549a94c1f8f8d7583979183d6e7R511

- Is block_number also needed? I think so.

  - https://github.com/nazar-pc/abundance/compare/main...block-layout#diff-f0ea9d8b207164fd2fa89ea59ca48f52bf2dc549a94c1f8f8d7583979183d6e7R473
  - Parents will have the full header.
  - The BlockNumber is available there so this is why it may not needed in the summary of shard
    block information.

- What is future_proof_of_time?

  - Different machines will take different amounts of time to generate a block. This may be
    advantageous for someone that can generate it faster.
  - Noticed that everyone has their PoT and add an artificial delay. You can produce a solution but
    you need to wait for the next PoT before you can publish it.
  - We may be able to remove this if we think if this doesn't add much. For now it makes total
    theoretical sense.
  - Fundamental reason, increase the fairness for farmers and have a deterministic point of sync in
    block proposal (otherwise someone could start going faster).
  - Original challenge: The time it takes to generate Chia PoS, that it was adding additional delay
    in the consensus critical path and it really impacts farmers with low hardware capabilities.
  - This may not be a concern once this is not introducing additional delay according to your
    hardware capabilities.

- What is the next_solution_range?

  - Every 216 blocks we have a new solution range and it should be valid for the time that you are
    generating the block.
  - This is essentially the difficult.

- I think BeaconChain should also include child_shard_blocks.

  - Fixed in the latest version:
    https://github.com/nazar-pc/abundance/compare/main...block-layout#diff-f0ea9d8b207164fd2fa89ea59ca48f52bf2dc549a94c1f8f8d7583979183d6e7R473

- We may be missing a field to submit segments created in the intermediate and beacon chain shards.
- Related to BlockHeaderConsensusInfo. I expect different shards to adjust their difficulty
  dynamically. Do we need this information to be included in the block or this is something that we
  expect to be available and retrievable on-chain.

  - This is the next_solution_range field and that will change sharded difficulty.
    > TODO: Zulip discussion about difficulty of child shards.

2. Discuss this comment about the window to validate a valid beacon chain.:
   https://github.com/nazar-pc/abundance/pull/220#discussion_r2084998638

> TODO: Attach figure: https://excalidraw.com/#json=E2u2173VCSc9eQBDFCmqz,IoT_llsUxCGmk2a-loamTg

3. What information should we store about child blocks in the parent, and where should we store
   them?

> TODO: MMR is lighter than a list because list grows linearly and MMR only logarithmically.

> But I'm not immediately convinced we need either. There will be some amount of data that we'll
> need to store about older blocks to support reorgs, that I don't think is mentioned here yet and
> may or may not be separate from verification of something that is stored within those child shard
> blocks.

> For verification of something that is within a block we need for that block to be "confirmed" (it
> is currently not defined what that means) by the beacon chain and then we can basically pick any
> path from the current beacon chain block referenced by a shard to generate a proof. In fact I
> think there are several options here:

> we can use beacon chain's MMR to go back to the older beacon chain block and descent from there we
> can use the latest beacon chain block, descent into the target shard and use its MMR to go back in
> time to some older block that contained information we're interested in could be a combination of
> these two and we can also use middle shard (if any) for additional "time travel" We need to think
> what would make the most sense in terms of complexity, efficiency, what is the most natural or
> canonical way to do it, etc. It might be the case that the things we store for light client
> verification are actually more than sufficient and we don't need extra maps. Or maybe we could
> benefit from an extra storage, but we'll keep a single "tip" entry for each shard instead of all
> or some number of recent blocks. I don't have answers for these questions as I have not spent too
> much time thinking about it yet.

> Regarding storing some recent number of blocks, we can store only the blocks that haven't yet been
> included in a segment

> Blocks that are at over 100 blocks deep can effectively be treated the same, at least for some
> purposes.

- The header includes the chain of block headers inside the parent block.
- The chain blocks are also arranged as a tree where we can proof that the block was committed in
  the parent block.
- We can traverse trees for the beacon chain.
- The suffix contains the body hash (we may have not only transactions but other things) and the
  state root.
- If we want to verify something for state root I would have to go deeper in the tree.
- We can use user contracts to be able to generate efficient proofs if needed.
- The red box from the figure is known before pushing transactions into the block.
  > TODO: Attach figure for the header:
  > https://excalidraw.com/#json=E2u2173VCSc9eQBDFCmqz,IoT_llsUxCGmk2a-loamTg

4. Syncing a shard from scratch:
   https://subspace.github.io/protocol-specs/docs/consensus/consensus_chain

- Syncing a shard from scratch.
  - We don't need necessarily the beacon chain synced from start, we can probably sync both from
    scratch (a little bit ahead or in parallel). We can probably sync beacon chain and shards in
    parallel.
  - Everyone would probably use Subspace's snap syncing to sync. With archival history we don't need
    archival nodes. Only indexers will need some access to the whole history, but there may store it
    in a different.
    - Historical context about syncing:
      - There are three mechanisms described in the spec: DNS from genesis, snap-sync, and recent
        history syncing.
      - There is a problem. If there is a big gap from the head to your latest block right now you
        can't do fast syncing. From 2 days ago to know you can't jump (in the current
        implementation). We should be able to always jump to fill in the gap.
      - Full-sync from genesis analogous from Substrate wouldn't work because we don't expect
        archival node to exist.
  - We don't see big blockers here, we just mention it and move to propose blocks.
  - Parallel workers for each shard and sync in parallel.

5. Discuss high-level of re-org management to describe the spec.

- We have PoT interval. We look back and look for two intervals back for entropy. We look for PoT
  injection delay.
- What this means is that if you don't see the block in red or re-orgs it doesn't change the PoT.
- We can use a deterministic interval to determine what needs to be the minimum view of the beacon
  chain that nodes need to see. If you haven't seen that block then it is invalid.
- @nazar: The complexity of implementing may not be worth it. This is similar to often blocks.
- It is strictly not necessary to have this. You don't roll-back but also extended.
- Make transactions mortal. Have a 100 blocks mortality.

7. What are the current blockers that you have? I feel more useful when I can start surfacing the
   high-level end-to-end and then give you feedback with something specific (as you are the one that
   has more context about the internals).

- Being able for a solo block to start generating blocks. To do this we need to be able to create
  segments and farm.

Next: 6. Do we need a section that describes the genesis of shards?

## Meeting 2025-05-16

> Goal: Surface the requirements for shard membership so we can make progress on the high-level
> design and related literature.

1. The accidental computer and ZD0 paper.

- Discussion about ZD0 paper and the accidental computer.
- Getting into the foundational concepts and build vertically from there.
- This surfaces a problem that we already identified which is the need for a proof not only of the
  availability of the segment, but also of the data being correctly encoded. Unfortunately, this
  still doesn't solve the problem of proving that the segment includes the right blocks.
- How can we proof that the segment includes the right blocks? Not only that the segment has been
  encoded correctly and that it is available?
- We could use ZKVMs but that won't be efficient for commodity hardwares at this point.
- Probabilistic proof of inclusion of blocks in segments anchored to the sampling proofs.

2. Can you explain a bit what you mean by this?

> What I think can be done about that is to commit not to "physical" shards, but to "imaginary"
> ones. Then we take imaginary shard number and do a simple operation like modulo division by the
> number of "physical" shards to figure out which shard we're actually farming on. That way once new
> shards are introduced, some farmers will switch to them. This means Solution will likely commit
> not to shard_id, but rather to some other variable, like a seed of some sort.

- Imagine that we have the system working for some time and how we can bootstrap it so farmers are
  assigned to it so we remove the imbalance.
- It would be nice if we can re-shuffle using consistent hashing.
- We create local randomness and we choose a number that assigns you to a specific shard.
- You then are re-assigned with some probability to a different shard. Announce beforehand and you
  have a window to check, ideally without replotting.

- Fundamentally we can't force farmers to do anything.
- We can influence the reference implementation. Pick a number for each disk that you have.
- We should anchor the shard membership to the farming process and winning solutions.
- Making it based in identity the election instead of some local randomness. Even if you happen to
  be in some shard you can be re-assigned to a different one. It's hard to be in the same shard
  twice.
- I don't like the auditor. We should embed these mechanisms in the protocol. Parallel operation for
  core execution and data availability sampling.
- Longest-chain can fix the sampling. Use consensus rules instead of fraud proofs.
- Dishonest majorities can potential build longest chains. Build a longest chain that is honest and
  we need honest majority.
- Assume that there is an honest majority always in the shard and try to enforce it. Pause if this
  is dishonest.
- Check David Tse paper about how the epoch duration and what are trade-off between the epoch size
  and security/overhead.

- How easy is to pause the shard? Is this a problem?

  - This is not a deal breaker.
  - How quickly can we make this rotation? What is the ideal target time for shuffling epochs?
    - Beacon chain is observing child shards and we can join and figure out what is going on. The
      fact that we are seeing what is being committed in the beacon chain is important.
  - How can we make membership resilient reshuffling?
    - AI: Papers about sharding and membership.

- Looking for ways to avoid fraud proofs at all if possible. This would remove a lot of complexity.
  Bribing and collusion may be big problems.

- Re. consistent hashing: I think this is a good idea with periodic reshuffling if we are fine with
  just a small number of farmers being reassigned.

3. Review the requirements for shard membership.

- Do we want on-demand membership where farmers can decide where they farm, or do we want the
  protocol to dynamically assign them to a shard?
- How I am thinking about this (hybrid model):
  - When a farmers wants to farm it needs to assign a plot to a specific shard.
  - Additionally, its power can be used by the protocol to assign it to a shard that is under-served
    in terms of power (weak security). Approach similar to merge farming.
  - The way in which farming works, each plot gets a ticket for the shard that is primarily or
    secondarily assigned to.
  - Secondary farming is "semi-dynamic". Plots are re-assigned to shards accounting for a
    sync/warm-up time of approximately 1 hour.

# Meeting 2025-05-21

- Really happy that the block header work has unblock a lot for me (now I now how to refer to things
  i.e. `IntermediateShardBlock` and we can reason about the flow of information more concretely).

1. child_shard_blocks is the root and the underlying block information is in the
   intermediate_shard_blocks? Are these fields redundant?

   - Check OwnedBeaconChainBlockHeader (i.e. Owned versions of the data structures) as they are
     easier to read.
   - We can check the fields that we are writing through a buffer.
   - We are sending the whole bundle of information to the beacon chain.
   - `IntermediateShardBlockBlockInfo` is the thing sent to the beacon chain and to communicate.

2. Block submission verification logic. Is it worth me helping with describing the logic for this or
   do you have all the information that you need?

   - This is solved! We will have to define what are the blocks and this is the header.

3. What is the block header seal?

- Only has the block signature and the type of signature used for the block.

4. Discuss the flow for segment submission and super segments.

- For every segment root we need to wait to confirm that they are final before submitting them, so
  not in the immediate block because that way we don't need to handle reorgs.
- Leaf segment roots shouldn't be propagated immediately up because then we can't wait for the delay
  required to validate that things are final.
- Requirements / Changes I would do:
  - Add to the segments roots also the number of shard it belongs to and the segment index. When it
    propagates to the beacon chain we can stash it somewhere in the storage and then we can use it
    to create the super segment and we can deterministically generate it.
  - Once we see it as stable we can create the super segment.
  - We can create super segments deterministically but it is dynamic, we only do it when is stable
    in the beacon chain.
  - AI (adlrocha): How we can consider this stable and what is the logic here.
    - Literature review of freshness of routing table.
    - Stabilisation of graphs and how we can consider that a segment is stable.
    - Any time we have a challenge and freeze confirmation of that shard until we understand what's
      going on.
    - Problem: DDoS and force forge to censor.

5. Discuss the realisation that all critical protocol mechanisms should rely on the longest-chain
   rule to make it simple to reason about and implement (block reorgs, segments verification, etc.)
6. I am planning to close the block header discussion PR if there is nothing else that we need to
   surface from there and keep it as internal notes. Also planning to keep all this notes in a
   separate branch?

7. Block rewards and incentives for the system.

- We won't fit u64, we need u128 and why not use all those units.
- We have a bunch of shards.
- We will say "every shard gets u128/n_shards", not uniformily but more for the beacon chain and the
  parents and a bit less to leaves.
- There is a reward pool in the blockchain and every time we have a block we have a reference
  subsidy. They may get less if there is utilisation, because there are fees and they don't need
  subsidies. We would still have something to give, there is a straight line until the pool lasts.
- The incentive of joining new shards is that the pool is untouched.
- There is a subsidy by design in shards. Maybe just a straight lines for a 100 years.

8. Look into https://abundance.build/book/Contribute.html

# Meeting 2025-05-23

1. The super segment is the trigger for confirming the global index for a shard segment (so it
   should be considered final when created).

> Notes in-line in segment proofs discussion

> NOTE (Q): Include a field in the shard block that identifies the list of verified segment indices
> from the global history so that it can be used to create the longest-chain rule?
>
> Doing all of these verifications manually would be really inefficient, here is were having the
> data availability layer, and a common broadcast channel for proof announcements will be key.

7. How can we ensure that the segments is valid? The verification of segments is part of the
   consensus rules. We should add a field to blocks that includes proofs that something is
   unverifiable and force to trigger a re-org. As part of the longest-chain rules there may be
   blocks that force to abandon the current history and prioritise another longest chain?

8. TODO: Proof that a segment is part of the block history? Is a recursive combination of tree
   proofs.

- Important for definition (data availability layer for segment verification
- Longest chain rules become key (everything should be embedded in the longest chain rules). This is
  how we remove fraud proofs.
- How does this impact plotting?

### Handling chain re-orgs.

- The main data structure that is impacted by re-orgs are blocks (see image from Excalidraw).
- Information about new blocks in a child shard is immediately propagated to the parent.
- Re-orgs are handled as part of the longest-chain rule of all the shards.
- Upward reorgs are easily detected, i.e. leaf or intermediate shards that suffer a re-org. As
  blocks are being submitted to the parent, the parent is able to identify that there was a re-org.
  This requires no immediate action from the parent (apart from updating its own view of the head
  and most recent blocks for the child shard --more about this in a minute--). Segments are not
  propagated immediately so there is no need to perform any actions over this.
- Reorgs from intermediate shards do not involve any immediate action from its child shard, the only
  thing is that all the blockchain information from child shards that have been reorged need to be
  re-submitted in subsequent blocks (but this shouldn't have any impact).
- Beacon chain reorgs are hte only ones that trigger actions in the lower levels of the hierarchy.
  When there is a re-org in the beacon chain, this triggers a re-org in all child shards. The re-org
  is easily handled by the longest-chain rule in the child shard. In the next block being proposed,
  the new block needs to point the most recent block that has a valid beacon chain reference after
  the re-org. From there on the operation is just the same.

> TODO: Reason about heaviest chain when we think about re-org. TODO: Delay for the beacon chain
> Reference so 1-2 blocks re-orgs. Proof-of-time injection.
>
> - Injecting to the future depends on the block that we were generating.
> - The PoT injection determines what will be the randomness 50 slots chain in the future.
> - This should impact the beacon chain reference that the block that chooses.
> - What block in-between we choose. Fresh enough so that it doesn't introduce a lot of delays.

> TODO: What is the block time. Should we use 6 seconds. We can consider what we do with computation
> to increase the block time and reduce the critical path.

### Segments submissions.

- Every parent (intermediate shards and the beacon chain) keeps a view of the current state of their
  child shards through the most recent blocks and segments that they are submitting. For each
  segment this view tracks the block in which it was propagated. The main reason for this is that
  for each recent block a probability of re-org will be computed for each block. When this
  probability of re-org reaches over a 99%, the intermediate shard will propagate the segments for
  the block that reached this value.
- In the same way, the beacon chain keeps track of the `own_segments` and `child_segments` from the
  intermediate shard, and will only consider them for inclusion in the global history (and into the
  super segment), once the probability of re-org is over 99%. This is done to avoid having to reorg
  the super segment and the segments that are part of it.
- As soon as a segment is created in a child shard, the data availability layer will be checking
  that it is correctly encoded and can submit challenges that the segment is not valid.
- When the block that includes that segment arrives to the beacon chain, the beacon chain will pause
  the commitment of new blocks until there a re-org that reverts the challenged segments, or a
  counter-challenge is sent reverting the failure situation.
- All of this is handled through the proposal of new valid blocks submitted from the lower to the
  upper layers of the hierarchy.
- With this, we add a dynamic waiting time for segments that depend on their probability of re-org
  that gives enough time to consider the segments final and to challenge potential misbehaviors and
  mistakes.

```
shard1: blk1 - blk2 - blk3
      segment1 (blk1)
      segment2 (blk2)
      segment3 (blk3)
```

The value of the probability of re-org can be computed as:

```rust
Prob (blocks_replaced) = (2*delta/T)^(blocks_replaced)
* z - blocks replaced
* delta - Time to first block propagation
* T = average time between blocks
```

> TODO: Read
> https://abundance.zulipchat.com/#narrow/channel/495788-research/topic/Shards.20dynamic.20difficulty.20adjustment/near/520217673

> TODO: Data availability layer:
>
> - What happens if a block (recent or deep) is not available and how are these challenged handled.
> - How can we recover from a block or a segment not being available.

> TODO: No pseudocode or verification functions: Step-by-step instructions for how to do this.

> TODO: Data availability currently works by walking the DHT and finding if a piece index exists. We
> can use a local piece index to sample this. Cache those for a small amount of time. We can try to
> sample them without relying on a data availability. Maybe we can propagate segments immediately.

> TODO: We can still propagate segments in leaf shards immediately from the intermediate shard?
> Unfortunately the beacon chain has no knowledge about if the leaf shard has re-orged.

> TODO: Maybe we can propagate the segments right away and then wait to generate the super-segment
> when is final. Nice-to-have: to have segments available in the beacon chain as soon as possible.
> Nice-to-have: Having a pubsub channel to broadcast the segments. Check how it is currently done
> the availability for the segments in Subspace with DSN.

> NOTE: Farmers are stable in the network so they can be considered persistent.

## Meeting notes 2025-05-28

1. (addressed) Segment submission step-by-step discussion with segments immediately available in the
   beacon chain ready.

- Discuss the final_segment_root field in the `IntermediateShardBlockInfo`.
- Add PR already for review? Yes, let's do it and move to membership allocation from here.

- AI:Segment index and shard index need to be propagated too up.
- Use the index instead of the root to confirm.

2. (addressed) Discuss blockchain reference setting in the block.

   > Note: How is the beacon chain reference required to validate blocks chosen by farmers in
   > lower-level shards?
   >
   > Protocol-wise, any valid reference for a valid beacon chain block can be used as long as it is
   > at a higher height than the one from the previous block in the shard and a higher slot, and as
   > long as it is not recent enough to not have been seen by the rest of the nodes in the shard and
   > thus have a high probability of being rejected as invalid. However, for the reference
   > implementation we will set a deterministic number of blocks for all nodes determined by
   > `BLOCKCHAIN_REF_DELAY` that will be set to `POT_ENTROPY_INJECTION_INTERVAL / 2` to allow for a
   > few blocks between PoT beacon chain randomness injections.

--- Action item ---

- Nazar (intuition about why randomness injection may be related):
  - If we take a block right before an injection interval.
  - Decision: we should reference the most recent one that is more than 6-blocks behind, otherwise
    you are not synced.
  - This way we force farmers to be as synced as possible with the beacon chain when they propose
    blocks in the shard and otherwise the farmer misses their opportunity to propose a block in the
    shard.

---

3. Discuss the requirements for data availability layer and how we want to implement it to
   understand the problems.

- This is a requirement for the validation of segments.
- Data availability layer over segments.
- Periodic sampling of chunks within pieces of a segment for a specific shard.
- Do we want this process to be best-effort or do we want to guarantee that the segments are being
  processed with some protocol mechanism?
- Ideally, we could have farmers that are proposing blocks to be forced to make some forced sampling
  before they can propose a block. The problem is verifying the availability certificate in a decent
  amount of time. Should we make it a background process?
- DHT is indexing segment roots. Can we embed a random segment and piece sampling mechanism for all
  farmers in all shards? Leverage the DSN as the data availability layer. (we can reuse the current
  encoding)

--- This is key ---

- Can we make greedy requests? Give me the X number of pieces.
- If we can implement the membership rotation and with high-probability we can have the membership
  change and check the segment root and only then they try to extend this change. When they submit
  the segment up they can check if the longest-chain is there. We can have a proof that there was a
  header of the leaf shard in this block. And in some way showing that there is a longest-chain. If
  we could build this many blocks in the leaf shard.

- For membership, we re-plot a bit and then move somewhere else.
- Approaches to shuffling:
  - Oblivious shuffling: All farmers are randomly assigned to all shards and the beacon determines
    the allocation every epoch (the more often this is done, the less vulnerable to attacks it is).
    The optimal allocation frequency is the key security parameter in this protocol, but the
    trade-off is that frequent re-shuffling may introduce additional overhead. We should compute
    those limits in both cases and model it.
  - "Swap-or-not" approach to minimise the number of farmers that need to move around.
    - This is so that not everyone changes and we can have faster epochs.
    - You can now the next shard in advance? We need to hide the leader because otherwise they can
      be attacked if we want to control a shard.
    - Local VRF to know in advance locally where we need to shard without releasing it to the rest
    - https://docs.rs/schnorrkel/latest/schnorrkel/keys/struct.Keypair.html#method.vrf_sign
    - ed25519 supports randomness? To make a signature of the randomness from the chain.
    - When we seal the block you include the randomness that proofs that you are entitled for that.
    - We need the signature to be deterministic to release it.
- Also see
  https://abundance.zulipchat.com/#narrow/channel/495788-research/topic/Dynamic.20difficulty.20adjustment.20and.20farmer.20allocation.20to.20shard/with/521003286
  to decide the parameters.

---

- Do we need blocks to be available for the whole history of a shard? Only for the segments that
  haven't been included in the global history, right? (otherwise, we can assume that they are
  available in segments).
- Same here, do we want it best effort or to be guaranteed by the protocol?
- Nazar:

  - We need availability for the blocks so we can sync.
  - Without blocks you can't verify anything else.
  - How farmers are distributed? If we assume valid nodes we may not need blocks. Blocks only need
    to be available syncing.
  - We need to do sampling of blocks so we can actually verify segments. You need to decode the
    segments and check the blocks.
  - Verify 2-3 latest segments and only continue if they are all good.
  - Make this part of the verification process.

- Any node can submit a proof of misbehaviour for a segment in the beacon chain that the next farmer
  will include in the block (we need a new field called `segment_reports` in beacon chain blocks).
  - These are reported in the beacon chain but can (and need) to be picked up by farmers in the
    corresponding shards to act accordingly.
- The farmer will ideally check the proof before including it and this opens the window for
  resolution that pauses the shard until a re-activation report is provided.

- With the requirements decided build the data availability layer.

4. Membership selection protocol (impact farming --and potentially plotting).

- I think we should maybe address this already as it may impact how we do farming and potentially
  plotting.
- The central objective is to design a membership selection mechanism that effectively addresses
  three interconnected goals: ensuring the load balancing of "power" (plotted space) across all
  shards, maintaining an equally high and consistent level of security for each shard, and
  preventing any dilution of the overall network's power or security during the sharding process.
- **We need mechanisms to monitor what is the power in each shard (through adjusted difficulty?).
  Can we have some other way? How does Subspace now the total storage plotted in the network if it
  is permissionless?**
  - Block time is a good indicator of the power in the network.
  - This may help with load balancing farmers along shards.
  - Re-shuffle by plot.
  - It may take them a while to re-plot and they may land in many shards.
- When is plotted space from farmers effectively proved, only when drawing a solution?

- Requirements:
  - First requirement for secure membership selection is a distributed randomness beacon (which we
    have).
  - A nice-to-have requirement is to have a deterministic allocation mechanisms that allows light
    clients to identify current members in the committee of a shard without requiring the whole list
    or any external information not available to them in a verifiable way (i.e. valid block
    headers).
- Approaches to shuffling:
  - Oblivious shuffling: All farmers are randomly assigned to all shards and the beacon determines
    the allocation every epoch (the more often this is done, the less vulnerable to attacks it is).
    The optimal allocation frequency is the key security parameter in this protocol, but the
    trade-off is that frequent re-shuffling may introduce additional overhead. We should compute
    those limits in both cases and model it.
  - "Swap-or-not" approach to minimise the number of farmers that need to move around.
    - This is so that not everyone changes and we can have faster epochs.
    - You can now the next shard in advance? We need to hide the leader because otherwise they can
      be attacked if we want to control a shard.
    - Local VRF to know in advance locally where we need to shard without releasing it to the rest
      of the network.
- What are the technical requirements for a farmer to propose blocks in a shard? (this will
  determine what we can do from a membership selection perspective).
  - Be connected to a full-node in the shard that is synced?
  - Access to the last X blocks?
  - Be a light client?
- Design questions:
  - How often do we need to re-shuffle?
  - How do we ensure that the new committee is able to propose blocks in their assigned shard?
  - What is the optimal size of the committee depending on the storage and the shard level?
  - What is the deterministic process of farmer selection?

> Idea: farmer's base shard assignment could be deterministically derived from a secure hash of
> their unique plot ID, which is generated from public keys and pool information. This could provide
> a stable "home" shard for a farmer's plots, simplifying data locality and reducing churn compared
> to purely random assignment for all duties. Subsequent active duties, such as block proposer or
> attester, could then be assigned via random re-shuffling within this deterministically assigned
> shard, combining the benefits of stability and unpredictability.
>
> - I am thinking about embedding into the farming process the allocation so that is part of the
>   core consensus and we don't need something that works in parallel.
>
> - To effectively encourage load balancing and equitable power distribution in a Proof-of-Space
>   system, incentives could be dynamically tied to a farmer's willingness to re-assign their plots
>   to under-utilized or high-demand shards. This could involve adjusting block rewards or
>   transaction fees based on the current load and "power" distribution within shards.
>
> - We can use a "swap-or-not" shuffling strategy with a probability according to the need to load
>   balance to minimise the number of farmers that need to be re-assigned.
>
> - We can determine the optimal size of the committee depending on the storage and the shard level.

> From:
> https://abundance.zulipchat.com/#narrow/channel/495788-research/topic/Shards.20dynamic.20difficulty.20adjustment/with/520219191
> nazar-pc: I've been thinking about this some more and wondering if there is still a way to make it
> work. One obstacle is that the plotting process commits to the size of the global history in
> segments. But what if it commits to a range of segments instead of a single segment? Another
> obstacle is that the algorithm for sector expiration makes farmer replot approximately half of
> their plot each time the history size doubles. But maybe it can be tweaked to something else? Or
> maybe we can at least make assignment based not just on sector identity, but sector identity + the
> history size when a particular sector was created, so it would be possible, but maybe not very
> often, that a single plot would actually be farming partially on one shard and partially on
> another. This together with using history size ranges might actually provide a decent option. I
> think it is very appealing if we can design a mechanism that allow to assign farmers to random
> shards completely permissionlessly.nazar-pc: If we crack this problem, it might just be the holly
> grail for us that may potentially allow us to not have fraud proofs, simply replacing everything
> with a delay, ensuring there was enough time for the honest farmers to take over whatever
> temporary dishonest majority may have formed on a particular shard.
