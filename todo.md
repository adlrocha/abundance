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

--- This is key -- pf-

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

# Meeting notes 2025-06-02

1. Membership selection protocol.

- Plots have a unique identity.
- Plots are the ones assigned to shards and that give power to propose new blocks.
- Sign with the key used for the plot to prove that you are the owner of the plot and verify the
  right membership.
- Requirements: Max number of shards a farmer can sync, level of stickiness (if any), time per
  verification, collusion time intervals

- Hash-based uniform distribution. Explored the use of a weighted one but we don't have information
  about whole list and we would need ordering. Can we have plots of a specific size always?

- Q: Can we have a specific size for plots?
  - The bigger the sector the less you are auditing.
  - This has some overhead because it requires you to have a lot of space in-memory.
  - Right now we have 1000 pieces per sector.
  - It would be nice if we have a hierarchical deterministic identity for the plot from a seed.
  - What is the minimum that they need to follow? 2 the minimum theoretical, 3 to simplify the
    implementation.
  - We would need to do rotation, if we don't sync a lot of shards we may have to increase the
    reshuffling interval.
    - Limit the maximum number of storage for allocation
    - Assume a limit where is the maximum that you can plot. Use this assumption for the design.
  - Complex solution with clear boundaries.
  - Trade-off: for an attacker that doesn't want to store a lot of things or store for long, the
    frequent rotation the best is for security and bad for farmers that are honest. We don't want to
    let attackers to be able to plot to force their allocation to land into a specific shard (1
    sector per 3 seconds, there may be a second per sector).
    - Aggregate identities and batch them to avoid single sector work. Use crypto to show that they
      were aggregated.
      - Nazar: "I would like more privacy and more anonimity" if we assign the whole plot with the
        same identity you can figure out that sectors belong to the same plot and thus for the same
        farmer".
      - 1 identity/1 plot
      - You can create a bigger plot with the same identity.
      - Think about the crypto
    - VRF of the allocation to the shard. We need to hide the information about allocation to
      prevent collusion and DDoS, be explicit about this.
    - Plots are currently at most 64TiB
      - Two plots with the same identity but different content. You determine the height of the
        blockchain history. Slightly older and newer sector and you can audit both. Both are valid.
        We want plots to also expire.
    - 1GiB plot is the minimum (one sector). We need fixed sizes and we need sector IDs.
    - Use average sizes of plots and use plot identities. Number of shards a function of the demand.

2. Segment verification

- Use the current sync mechanism to verify segments and report any misbehaviour.
- We don't need to check segments that have been archived in the global history because they are
  potentially part of plots and they are verified through re-plotting.
  - How are we currently checking the availability of segments in Subspace?

3. Next plotting / farming

   ---- Notes ---

- P(k attacker plots in Sj​)=(knj​​)(fattacker​)k(1-fattacker​)nj​-k- **Model (Binomial
  Distribution/Chernoff Bounds):** The number of attacker-controlled plots in a given shard can be
  modeled by a binomial distribution. Let k be the number of attacker plots in a shard. The
  probability of having k attacker plots in a shard Sj​ is:

  P(k attacker plots in Sj​)=(knj​​)(fattacker​)k(1-fattacker​)nj​-k

  More practically, we are interested in the probability that an attacker controls _more than a
  certain threshold_ (τ) of plots within a shard.

  **Chernoff Bounds** can be used to estimate the tail probabilities: Let Xj​ be the number of
  attacker-controlled plots in shard Sj​. The expected number of attacker plots in shard Sj​ is
  E[Xj​]=nj​⋅fattacker​.

  For δ>0: P(Xj​>(1+δ)E[Xj​])≤exp(-3E[Xj​]δ2​)

  This allows you to calculate the probability of an attacker gaining a disproportionate share of a
  shard.

  - **Correctness Criteria:** The probability of an attacker controlling more than τ of plots in
    _any_ shard should be below a very small, acceptable threshold. This informs decisions about NS​
    and the overall security assumptions.

### Probability of Attack (Collusion)

The goal of shuffling is to make it statistically improbable for an attacker to control a
supermajority (e.g., 2/3, 1/2 + 1, or 1/3 for liveness attacks) of plots within a single shard, even
if they control a significant fraction of the total plots in the network.

- **Assumptions:**

  - Total number of plots: NP​
  - Number of shards: NS​
  - Average plots per shard: k=NP​/NS​
  - Fraction of plots controlled by attacker: α∈[0,1] (i.e., αNP​ plots are malicious).
  - A successful attack on a shard requires τ fraction of plots in that shard to be malicious (e.g.,
    τ=2/3 for safety, τ=1/3 for liveness).

- **Model (Binomial Distribution):** For a _single specific shard_, the number of malicious plots X
  can be modeled as a binomial distribution if plot assignments are truly random and independent.
  X∼B(nj​,α), where nj​ is the number of plots in shard j. Assuming uniform distribution, nj​≈k.

  The probability that a specific shard has at least τnj​ malicious plots is:
  P(X≥τnj​)=∑i=⌈τnj​⌉nj​​(inj​​)αi(1-α)nj​-i

- **Model (Chernoff Bounds - for tail probabilities):** This is often more useful for bounding the
  probability of _any_ shard being compromised. Let Xmalicious,j​ be the number of malicious plots
  in shard j. The expected number of malicious plots in shard j is E[Xmalicious,j​]=nj​⋅α.

  If you want to find the probability that Xmalicious,j​ exceeds a certain threshold (1+δ) of its
  expectation, i.e., P(Xmalicious,j​>(1+δ)E[Xmalicious,j​]):
  P(Xmalicious,j​>(1+δ)E[Xmalicious,j​])≤exp(-3E[Xmalicious,j​]δ2​)

# Meeting notes 2025-06-04

1. When is PoS proved, and can we use this to prove the size of a plot?

### Proposed model of membership allocation.

We will divide the membership allocation protocol in two stages:

- Plot allocation
- Difficulty adjustment (load balancing) We are going to consider the first one mandatory, and the
  second one is an idea that I came up with to improve the quality of the system, but it shouldn't
  be needed for the system's correctness. Having two stages may allow us to minmise the number of
  times that a farmer needs to be re-assigned.

- Assumptions:

  - The minimum number of membership is the plot. Plots are uniquely identified, and they will
    determine the shards with which the farmers need to sync.
  - Plots will have a `MAX_PLOT_SIZE` that determines the maximum size of the plot in bytes.
  - Only leaf shards are considered for the membership allocation. When a farmer is assigned to a
    leaf shard, it will need to sync with the leaf shard, its parent shards, and of course the
    beacon chain.

- Protocol parameters:

  - `NUM_SHARDS`: The number of leaf shards in the system.
  - `MAX_PLOT_SIZE`: The maximum size of a plot in bytes.
  - `total_storage`: The total storage capacity of the system in bytes.
  - `plot_j`: Identity of a plot with ID `j
  - `MEMBERSHIP_RESHUFFLE_INTERVAL`: The interval between membership reshuffles in slots.
  - `NEW_MEMBERSHIP_WARMUP_INTERVAL`: The interval between the membership reshuffle and the new
    membership coming to effect in slots.
  - `BALANCING_INTERVAL`: The interval between difficulty adjustments in slots. This is not a full
    membership reshuffle, but a partial re-balancing for misrepresented shards.
  - `BALANCING_THRESHOLD`: The threshold for the difficulty adjustment. If the difficulty of a shard
    is below this threshold, it will be considered misrepresented and the difficulty will be
    adjusted.
  - `BALANCING_WARMUP_INTERVAL`: The interval between the difficulty adjustment and the new
    difficulty coming to effect in slots.

- Membership allocation protocol:

  - Every `MEMBERSHIP_RESHUFFLE_INTERVAL` slots, the membership allocation protocol is executed.
  - The target storage per shard is first computed as
    `target_storage_per_shard = total_storage / NUM_SHARDS`.

    > Q: Can we have the number of plots in the system? If this is the case, it would be better to
    > compute total_storage as the sum of all plots considering they have `MAX_PLOT_SIZE`.
    >
    > - We don't have the total number of plots so we need to go with total storage and the number
    >   of plots may not be balanced, but it shouldn't impact the analysis.

  - The number of plots to be assigned per shard is computed as
    `plots_per_shard = floor(target_storage_per_shard / MAX_PLOT_SIZE)`.
  - With this in mind, the specific shard for each plot is computed randomly leveraging a VRF of the
    plot identity, feeding the randomness for this epoch in something like:

  > NOTE: plots_per_shard gives us nothing because we can't balance the number of plots per shard as
  > we don't know the total number of plots in the system.

  ```
  shard_id = VRF(plot_identity, epoch_randomness) % NUM_SHARDS
  ```

  > Note: The specifics of this computation won't modify the protocol as long as it is random and
  > uniform.

  - We can compute the probability of a farmer being able to attack a shard as:

$$
P(X_k \ge k_\alpha) = \sum_{j=k_\alpha}^{K_M} \binom{K_M}{j} \left(\frac{1}{N}\right)^j \left(1 - \frac{1}{N}\right)^{K_M - j}
$$

> Note:
>
> - Plotting allocation (the attack for this)
> - Bribe farmers (collusion attack, sustained attack) --> Look for papers that objective compute
>   the probability of bribing or something like that.
> - Attacks in the warmup interval (TODO: I am missing this one)

where:

- ka = is the number of shards that the attacker needs to get control of a shard. For a
  longest-chain protocol like ours 51%. This can be computed as
  `ka = (percentage_storage * target_storage_shard) / MAX_PLOT_SIZE`
- KM = total number of plots owned by the farmer = `farmer_storage / MAX_PLOT_SIZE`
- N = number of shards
- SM = total storage controlled by the farmer.

- Optimal reshuffling interval.

  - The epoch duration should be a function of the probability of a sustain attack and the cost of
    re-shuffling for farmers, where w1 and w2 are our own subjective weights on the importance of
    each:

```
optimal_epoch = w1 * probability_of_sustain_attack + w2 * cost_of_reshuffling
```

> NOTE: cost_of_reshuffling needs to have a minimum value which is the overall cost to change
> shards, and the maximum being the time to plot enough plots to get control of a shard.

- The probability of a sustain attack is a decreasing function of the reshuffling interval.
- The cost of re-shuffling is an increasing function of 1/reshuffling interval.
- So shorter epochs --> higher cost --> lower probability of attack.
- Thus, reshuffling interval should be ideally << time for an attack.
- We can use as a baseline the empirical value that the plotting throughput that we can currently
  have is ~3.6T/hour.
  > Q: The size of the network would determine the size of the shards and we need to decide this.
- We can leverage `MAX_PLOT_SIZE` to determine the optimal reshuffling interval.

> Q: What should we include in the cost of re-shuffling?
>
> - Syncing with the new shard. (anything else?)
> - Discovery of peers.
> - Fetch the blocks
> - Sharing transactions

> Q: What is the target time of attack?
>
> - This should be determined by the time that an attacker needs to create plots that with high
>   probability allows to get control of a shard (see probability computation from above)
> - Also add any collusion metrics that we think are relevant.

- Load balancing interval
  - We can compute the total difficulty of the system through the solution range.
  - From the solution range we can get the sectors that range that solution range.
  - We can get the solution range for each leaf shard (and even intermediate shard).
  - We get the over-represented and under-represented shards and run the membership allocation
    protocol over the farmers in those shards. This should trigger a load-balancing among all the
    farmers from these.

> Next steps:
>
> - Complete the analysis with the missing attack.
> - VRF do not worry about it but we need to analyse the warmup interval potential attacks, and the
>   DDoS surface attack once the VRF determines the allocation (and how we can know that is the
>   active membership).
> - Write down a discussion with the full model so that it can be understood by human beings and we
>   can have it as a base.
> - The size of the network according to the total storage and the number of shards needs to be
>   determined.
> - Let's consider the minimum interval of re-shuffling one-hour and let's understand if there are
>   blockers that could kill that.
> - Think about the economic cost of the attack. Attackers use computation and honest nodes are
>   using storage as the fixed cost resource.
> - Theoretically we can increase the cost of plotting if needed and they can create a chia table
>   when they generate the challenge.

> Nazar: The attacker, if they control the majority of a shard they can drop blocks and make it look
> as balanced and "beautiful", so we should never allow for this (this would also break the
> balancing idea).
>
> - Selfish mining.

> Note:
>
> - See explorers for some numbers on the order of magnitude that the Autonomys network currently
>   has: https://astral.autonomys.xyz/mainnet/consensus
> - H9 allows renting storage and makes a comparison between different PoS networks.

# Meeting 2025-06-09

1. Discuss no attacks in the reshuffling interval, fully adaptive adversary from free2shard.

- What if we have a list of plots and I can grind the identities to assign the plots.
- Nicehash should be considered for the attack (is this static or adaptive adversary?)
- PoS is burning coins while if we consider renting hardware we are not in the same game.
- The only reason why bitcoin is secure compared to our model is just scale, otherwise it would have
  the same vulnerabilities.
- We need to be mindful about the number of cores directed to execute transaction in shards which
  means that it may limit the number of shards we can have (and sync with from a node perspective).
- We may want in testnet to have just 2 leaf shards so that everyone is following almost everything
  and we can have full security while making sure that the protocol is correct. We may want to
  introduce an additional shard where a subset of farmers is not following it so we can evaluate the
  correctness and the implementation in something closer to the real scenario.

2. Share the Python script and evaluate parameters.

- Next steps:
  - Review comments from segment commitments and super segments that is blocking Nazar.
  - Python script improvements for membership allocation.
  - Read the PR: https://github.com/nazar-pc/abundance/pull/278

# --- TODOs for the modelling script ---

# TODO: Add a parameter that considers the size of the history?

# TODO: Measured storage? How much malicious storage we can have in any shard to corrupt it? (51% or less?)

# TODO: Figure out how much it costs to pull off that attack.

# TODO: The cost such be a substantial fraction of the whole network. We want to make sure that we have morel that the half total space to attack the shard. The cost should be higher than if I dedicate the plots honestly.

# TODO: All the computation the world should be used for something, and this protocol should enable it.

# Meeting 2025-06-11

1. Type of attacks

- Share the changes in the model with throughput and storage limited attacks.

1. Discuss how the history size impacts the probability of attack.

- The protocol is storing the whole history. We need to force farmers to re-plot periodically to
  update them for the new global history.
- The history size can be selected in a way that the plot will expire earlier but I choose valid
  sectors that belong to the previous history.
- I can create x5 times the expected size because I commit all sectors to different history sizes.
- 1PiB of SSDs. Create multiple 65TiB of the same plot to the same petabyte. You would move the
  whole petabyte.
- Half of the plots will expire every epoch.
- We want farmers to re-plot but we don't want them to do it that often because otherwise we are
  PoW.
- Pieces won't be plotted until the window is stopped. Mechanism for plotting so that we don't plot
  often.

- Storage should be kept below the threshold of honest storage (so it is virtually unlimited but we
  want to limit it).
  - how does having bigger plots impact the probability of attack?
- TODO: 51% attack globally means the beacon chain is secure but what about the shards? What is the
  number in this case?
- TODO: Even if the plot is unbounded but the size is below than the honest majority and they have
  issues moving it around then it means we can be secure.
  - We can probably upper bounded with the size of the history size. This is the multiplier of the
    number of additional sectors that the attacker can do.
  - This will be an input in the decision on the number of shards that we can have. We can probably
    compute this.

1. Comparison with honest cost.

- We want to make rational honest plotting over attacking it even if attacking is a bearable cost.
- The yield should be more than what you put in.
- The cost of attacking should be a function of on-going normal cost of operation.
  - It is generally expected that this will not be profitable if you are trying to do it on-purpose
    buying hardware and operation. Maybe in economic of scale that may be possible. We should
    accommodate for the computers and general-purpose that wouldn't add big farms and we have edge
    honest computers.

---

To discuss next around segment submission:

- https://github.com/nazar-pc/abundance/pull/267/files#r2120139511
- https://github.com/nazar-pc/abundance/pull/267/files#r2120067069

# Meeting 2025-06-16

- Latex support for the blog (tried but I keep breaking the template)
- Share model to compute security bound for the protocol (30%-45% of the honest storage should be
  enough to secure the protocol).
- Discuss plot uniqueness

  - What does this mean practically to the farmer.
  - When will things expire and how they will expire.
  - Are we expiring things in large quantity?

- Notes on the reshuffling interval:

  - We can use the reshuffling interval to determine the number of reshuffling that we need to wait
    so several segments and a high population has checked segments.

- TODO: Modeling the interval shuffling in a way were we can be sure if we can have just this
  approach of membership allocation and no optimistic paths that require fraud proofs. This should
  be secure with high-probability.
- Probability of expiration check:
  https://github.com/nazar-pc/abundance/blob/72349dc2f0505be4da766e01dc5f1240acd4f22c/crates/shared/ab-core-primitives/src/sectors.rs#L237-L268
- TODO: What is the boundary in terms of finality so that we can live without fraud proofs? And if
  we can how much we need to wait?
- TODO: How to organise plots. Come up with the farming side to unblock Nazar.

  > TODO: Next step: Think about expiration of plots and how to handle it withe the plot uniqueness
  > model that we have.

  > TODO: How much do we increase the replotting compared to the current state in Subspace?
  >
  > - Half of the plot needs to expire every time that the history doubles.
  > - See
  >   https://github.com/nazar-pc/abundance/blob/72349dc2f0505be4da766e01dc5f1240acd4f22c/crates/shared/ab-core-primitives/src/sectors.rs#L237-L268
  >   for the probability expiration.

# Meeting 2025-06-20

1. Discuss fraud proofs and reshuffling interval model.
2. Discuss farming process.
3. Discuss sector expiration.

- Fixed window plot size
- Farmer elected window size.

- Before a block is confirmed in the beacon chain we need to ensure that it is final, so we need to
  wait to ensure that the reshuffling interval has caught any bugs.
- Check sync notes in Autonomys forum by Nazar:
  https://forum.autonomys.xyz/t/a-lot-faster-snap-sync/4847?u=nazar-pc
  - PoT is something that we need to validate. You need to verify it and in the last few blocks you
    verify the last few blocks and that can be expensive.
- The formal models we have limitations in both sides.

  - TODO: Update the script so that I include all of the models and we can check that they are
    overlapping when changing the security parameters.

- How does the window range for plots affect the inclusion of recent pieces.
- Plot ID. Sliding window for the history range.
- The only time if we have a big problem if all farmers have the same interval.
- IF you generate a plot you generate a public key and you determine the history size as the tuple.
- If you create the plot at different points of time, and the interval will start at different
  points of time.

- A key pair, public key hash, and an interval from which you are plotting to (e.g. sectors)
- Until you don't have 10 segments you can't start plotting.
- You can have an offset in addition to the key pair.
- For one farmer may be 0-9 and for the other 2-11.
- Different farmers will have different intervals. Some farmers may have to wait until plot 19. But
  other may be able to do 8-19. At random some will be able to get the recent pieces.
- Jumping window in interval sizes depending on some number determined in the plot id.
- The last complete range of segments will be 1-100 (this are sector indices). We commit to a range
  of history sizes instead of a specific history size. That range or few ranges are considered
  recent and the other is the old history.
- Look at selection algorithm for the sectors:
  https://github.com/nazar-pc/abundance/blob/d9174318f9bd0c6d794b85b6b160e4329c9f29f7/crates/shared/ab-core-primitives/src/sectors.rs#L173-L216

  > - TODO: We need to do some simulations to understand if the history is stored. Can we formalise
  >   this?

# Meeting 2025-06-23

1. Sector expiration and history size with plot ID uniqueness

- Farmers choose a random offset from zero to the range of history segments that we commit to.
- This offset will determine the size of the window that the farmer is plotting its sector to but no
  the specific window.
- Commit range influences piece selection instead of influencing the range of history sizes that a
  sector can be committed to.
- We can say that it expires like in subspace even if we use a range, and the ranges will be
  exponential in size, it follows the same trajectory as replotting. As you commit the offset it
  determines where the multiplication starts and we need to choose the parameters so the window
  sizes is determined.
- There is a pre-determined set of history sizes that you can commit to. The range that you commit
  with will determine where you can commit your sectors.
- You would choose the latest history size that you see for your range.
  - History size of 8
  - Orange farmer and the current history size is 3 segments and we want to create a new sector.
    What do you choose as pieces for this sector.
    - I can see the range that is available for me.
    - I can only choose from the range of thing that are in the past
    - That is where you choose from 0 to 1 because of your offset and your range, even if there is
      something more recent available I won't be able to choose from it.
    - It expired and now history size is 8.
    - I am committing to the history size of 8 and I limit the range.
    - Expiration rules so that we limit the range.
    - Exponential range so that it fits more segments so that the less often sectors expire. Is this
      true?
    - We can say that everything committed in 2x expired in 4x. There are two ranges at every time
      that are valid.
    - If we are at range N and it expired, N+1 is valid and N+2 is valid.
    - It will expire in the middle of the next range so that I am force to replot in the next
      interval.
    - Every next time there is less expiration but then we still have the same history size to
      commit to.

> TODO: We can immediately expire. The ranges are larger and we may be able to simplify the
> expiration logic. Explore the expiration so we don't have to guess when it will expire because you
> already know through your range.. Ideally every farmer commits to a different history size. Every
> single segment has a farmer committed to it.

> TODO: Think about how to make this explainable.

- Maybe every of these ranges are part of this plot ID and you end up in two shards at the same
  time?

> TODO: The most immediate priority is to have the script updated with the two models and start
> playing with the protocol parameters. It can also help implementing the expiration there.

## Meeting 2025-06-26

1. Conclusions from the script and the model.

- The reshuffling interval will always be one as long as the proportion of honest storage is above
  the security bound (we can ensure that we will always have an honest majority after a reshuffle in
  all shards).
- The reshuffling interval depends on the throughput from malicious nodes.

> TODO: Add descriptions about about the parameters and how the script works so anyone can run it
> and build upon it.

1. Expiration Logic

- The effective range should go below the latest history size.
- Initial range 0 to 0
- Share the code for the plot range so people can play with it.
- How much we are limiting the plot size for the history range?
- Do we actually maintain this properties.

## Meeting 2025-06-30

- Effective range update.
  - TODO: Share with Nazar.
- Ranges to see what has expired in the visualisation.
- Sector expiration validation.

  - Use this code as a base to share how I am thinking this should be verified:
    - https://github.com/nazar-pc/abundance/blob/419c7d8ef57912088cfdd4a71dfb1908f2fb7d34/crates/node/ab-client-block-verification/src/beacon_chain.rs
    - https://github.com/nazar-pc/abundance/blob/419c7d8ef57912088cfdd4a71dfb1908f2fb7d34/crates/shared/ab-core-primitives/src/solutions.rs
    - https://github.com/nazar-pc/abundance/blob/419c7d8ef57912088cfdd4a71dfb1908f2fb7d34/crates/shared/ab-core-primitives/src/solutions.rs#L542-L596

- Next steps till contract end.

  - Give me enough clarity so that I can implement it.
  - Leave enough documentation so that anyone can peer-review.
  - Simulation of the protocol.
    - Fork the spec and try to change the things that we need to change.
    - https://github.com/subspace/protocol-specs

- As the history gets bigger there may be some time that you may increase by 2x, what is the actual
  model behind it? Is there an upper bound or does it change it with history range?
