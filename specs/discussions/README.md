# Sharded Blockchain Security Analysis Tool

This tool analyzes the security properties of a sharded blockchain system where storage plots are
randomly allocated to shards through periodic reshuffling.

## Overview

The analysis evaluates three critical security aspects:

1. **System Security Bound**: Can the system tolerate the assumed proportion of malicious plots?
2. **Fraud Detection**: How effectively can the system detect fraudulent behavior through
   reshuffling?
3. **Plotting Attacks**: Can individual entities compromise shards by creating plots during
   reshuffle intervals?

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python farmer_allocation.py
```

The script will run predefined scenarios and output a comprehensive analysis table.

## Mathematical Models

### 1. System Security Bound (Chernoff Bound)

```
P(System Insecure) ≤ S * e^(-n(0.5-p)²/(3p)) < α
```

Where:

- S = number of shards
- n = average plots per shard
- p = global proportion of malicious plots
- α = acceptable probability of system compromise

### 2. Fraud Detection Model

```
P(fraud undetected for k intervals) = S * (p^n)^k < α_fraud
```

Assumes fraud detection through periodic reshuffling.

### 3. Plotting Attack Model

Analyzes whether entities can plot enough storage during reshuffle intervals to gain shard majority
control.

## Key Metrics Explained

### Security Indicators

- **Overall Security Status**: Summary of all security conditions
- **Max Tolerable Malicious %**: Maximum global malicious proportion the system can handle
- **Beacon Chain Security**: Whether the main chain remains secure (<50% malicious globally)

### Attack Analysis

- **Attack Definitely Succeeds**: Whether attackers have deterministically enough plots for shard
  control
- **Prob. Majority in Any Shard**: Probability that random allocation gives attackers shard majority
- **Max Shards w/ Perfect Targeting**: Upper bound on damage with perfect targeting

### Operational Metrics

- **Finality Delay**: How long users must wait for transaction finality
- **Sync Feasibility**: Whether the required data synchronization is practical

## Interpreting Results

### 🔒 Security Status

- **Secure**: All security conditions met
- **Insecure**: One or more security violations (details in parentheses)

### ⚠️ Common Warning Types

- `Exceeds Shard Security Tolerance`: Too many malicious plots globally
- `Single Entity Can Gain Shard Majority`: Plotting attacks succeed
- `Impractical Finality Delay`: Users must wait too long for finality
- `Beacon Chain Compromised`: >50% malicious plots globally

### 💰 Economic Interpretation

Compare "Plotting Attack Cost" vs "Honest Shard Cost":

- Lower attack costs indicate vulnerability
- Higher attack costs provide better security

## Critical Limitations

### ⚠️ Key Assumptions That May Not Hold

1. **Random Allocation**: Assumes plot allocation to shards is truly random

   - Real attackers might bias allocation toward target shards
   - Could make attacks more successful than predicted

2. **Independence**: Assumes independent plot creation across entities

   - Coordinated attacks not modeled
   - Economic incentives for collusion ignored

3. **Perfect Fraud Detection**: Assumes fraud detected perfectly after reshuffling

   - Real detection may be delayed/incomplete
   - Sophisticated attacks might evade detection

4. **Static Analysis**: Parameters assumed constant

   - No dynamic growth or adaptive attacks
   - Fixed economic conditions

5. **Simplified Costs**: Only plotting costs considered
   - No operational costs or market dynamics
   - No opportunity costs or ROI analysis

## Recommended Validation

To validate these theoretical results:

- **Simulation**: Test with realistic allocation mechanisms
- **Game Theory**: Analyze coordination incentives
- **Stress Testing**: Use adaptive attack strategies
- **Economic Modeling**: Include comprehensive incentive structures

## Parameter Sensitivity

Key parameters affecting security:

- `num_shards`: More shards → easier individual shard attacks
- `plotting_throughput`: Higher rates → more dangerous attacks
- `reshuffle_interval`: Longer intervals → more plotting time
- `max_plot_size`: Smaller plots → need more for majority

## Modifying Scenarios

Edit the `scenarios` list in the script to test different configurations:

```python
scenarios = [
    {
        "name": "Your Scenario Name",
        "num_shards": 10,
        "max_plot_size_gib": 64000,
        "total_network_storage_pib": 500,
        "plotting_throughput_tib_hr_per_entity": 100,
        "cost_per_plot_usd": 0.25,
        "target_reshuffle_interval_hours": 1,
        "assumed_malicious_proportion": 0.3,
        "system_security_alpha": 1e-6,
        "fraud_detection_alpha": 1e-9,
    },
    # Add more scenarios...
]
```

## Theoretical Issues Identified

Based on the analysis, potential theoretical issues include:

1. **Overly Optimistic Random Allocation**: The assumption that malicious actors cannot influence
   plot allocation may not hold in practice.

2. **Fraud Detection Model**: The model `P(fraud undetected) = (p^n)^k` assumes perfect randomness
   and detection, which may be too optimistic.

3. **Independence Assumption**: Real-world coordination between malicious entities is not captured.

4. **Economic Model Limitations**: The cost analysis doesn't include opportunity costs, market
   dynamics, or economic attacks.

## Contributing

When modifying the analysis:

1. Ensure input validation for new parameters
2. Add comprehensive documentation for new functions
3. Test edge cases and numerical stability
4. Consider the theoretical validity of new assumptions

## License

[Add appropriate license]
