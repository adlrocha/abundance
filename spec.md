## Questions
- How do votes work in block proposal?
	- They are winning chunks that are not the best solution. Only the best solution is added as the winning block, but all valid votes within range are eligible for rewards.
- Who stores the archived/cannonical history, and how are pieces downloaded from the network?
- Are there any transactions performed when the history is archived?
- Where is the state resulting from transaction execution stored?
- Can we have empty blocks?

## Stages of a shard generation.
- Genesis generation

#### Parameters for shards.


## Detailed design.
After a lot of thinking, I have come to the realisation that we can design our system building upon the Subspace protocol and all of its mechanisms. This have several advantages:
- We can build upon the security and the robustness of the Subspace protocol. If we assume that the Subspace protocol is secure, we can derive the security of our protocol from the security analysis of Subspace.
- The team is already familiar with Subspace, this will help with its implementation and with reasoning about its correctness.
- We are building upon a consensus algorithm that is operating in production, and we can learn from all the improvements and mistakes made so far (design and implementation-wise).

Let's focus first on the relationship and block generation between two different layers of the system. The global consensus layer and the shard layer immediately below. Ideally, the consensus should be recursive so that the system can scale infinitely below.

### Archiving




### Layer 1: Global consensus.
- The global consensus is the main chain of the system. It is responsible for orchestrating the lifecycle and the security of all the shards in the lower levels.
```
SegmentHeader
BlockContinuation
Block(s)
BlockStart
Padding
```