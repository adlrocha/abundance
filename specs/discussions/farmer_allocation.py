"""
SHARDED BLOCKCHAIN SECURITY ANALYSIS TOOL

This script analyzes the security properties of a sharded blockchain system where:
1. The network is divided into multiple shards
2. Each shard stores a portion of the blockchain data
3. Plots (storage commitments) are randomly allocated to shards via reshuffling
4. Malicious actors attempt to gain control of individual shards

THEORETICAL FOUNDATION:
======================

The analysis is based on three core mathematical models:

1. SYSTEM SECURITY BOUND (Chernoff Bound Application):
   P(System Insecure) ≤ S * e^(-n(0.5-p)²/(3p)) < α
   
   Where:
   - S = number of shards
   - n = average plots per shard
   - p = global proportion of malicious plots
   - α = acceptable probability of system compromise
   
   This bounds the probability that ANY shard becomes majority-malicious.

2. FRAUD DETECTION MODEL:
   P(fraud undetected for k intervals) = S * (p^n)^k < α_fraud
   
   Assumes fraud detection through periodic reshuffling where malicious control
   of a shard during interval i is detected in interval i+1.

3. PLOTTING ATTACK MODEL:
   Analyzes whether a single entity can plot enough storage during a reshuffle
   interval to gain majority control of one or more shards.

SECURITY ASSUMPTIONS:
====================
- Random plot allocation to shards (no targeting by attackers). Attackers want to control as many shards as possible without being detected.
- Independent plot creation across entities
- Perfect fraud detection after one reshuffling period
- Beacon chain remains secure (< 50% global malicious proportion)

LIMITATIONS:
============
- Assumes truly random allocation
- Simplified cost model (plotting cost only) for a basic economic analysis
- Does not account for network effects or economic incentives
"""

import math
from scipy.stats import binom
from prettytable import PrettyTable
import numpy as np


def calculate_shard_insecurity_probability(n, p):
    """
    Calculate the probability that a single shard becomes insecure using Chernoff bound.
    
    THEORETICAL BASIS:
    A shard becomes "insecure" when it contains >50% malicious plots. This function
    uses the Chernoff bound to estimate this probability given:
    - n plots randomly allocated to the shard
    - global malicious proportion p
    
    The Chernoff bound provides: P(M/n ≥ 0.5) ≤ e^(-n(0.5-p)²/(3p))
    where M is the number of malicious plots in the shard.
    
    INTERPRETATION:
    - Low values (e.g., 1e-10) indicate the shard is very likely to remain secure
    - High values (e.g., 0.1) indicate significant risk of shard compromise
    - Value of 1.0 indicates certain compromise (when p ≥ 0.5)

    Args:
        n (float): Number of plots in the shard
        p (float): Global proportion of malicious plots (0 ≤ p ≤ 1)

    Returns:
        float: Probability that the shard becomes insecure (has ≥50% malicious plots)
        
    Raises:
        None: Function handles edge cases gracefully
    """
    # Input validation
    if not (0 <= p <= 1):
        raise ValueError(f"Malicious proportion p must be between 0 and 1, got {p}")
    if n <= 0:
        raise ValueError(f"Number of plots n must be positive, got {n}")
    
    # If global malicious proportion >= 50%, any shard is likely compromised
    if p >= 0.5:
        return 1.0

    # Security margin: how much below 50% the global malicious proportion is
    epsilon = 0.5 - p
    if epsilon <= 0:
        return 1.0

    # Apply Chernoff bound: P(M/n >= 0.5) <= e^(-n(0.5-p)^2 / (3p))
    # This bounds the probability of having too many malicious plots in the shard
    try:
        exponent = -n * (epsilon**2) / (3 * p)
        return math.exp(exponent)
    except (OverflowError, ZeroDivisionError):
        # Handle numerical edge cases
        return 1.0 if p > 0.5 else 0.0


def calculate_system_security_bound(total_plots, num_shards, p, alpha=1e-6):
    """
    Determine if the entire system meets security requirements for shard safety.
    
    THEORETICAL BASIS:
    Uses the union bound to estimate the probability that ANY shard in the system
    becomes majority-malicious. The bound is:
    P(System Insecure) ≤ S * P(single shard insecure) < α
    
    Where the system is considered "insecure" if any shard is compromised.
    
    CRITICAL INSIGHT:
    This is a CONSERVATIVE estimate. The actual probability may be lower due to
    dependence between shard security events, but the union bound provides a 
    safe upper bound for system security analysis.
    
    INTERPRETATION OF RESULTS:
    - "meets_security_bound": True if system is theoretically secure
    - "system_insecurity_prob": Upper bound on probability of ANY shard compromise
    - "security_margin": How far below 50% the global malicious proportion is
    - Lower "single_shard_insecurity_prob" indicates better individual shard security

    Args:
        total_plots (int): Total number of plots across all shards
        num_shards (int): Number of shards in the system
        p (float): Global proportion of malicious plots (0 ≤ p ≤ 1)
        alpha (float): Maximum acceptable probability of system compromise (default: 1e-6)

    Returns:
        dict: Dictionary containing:
            - avg_plots_per_shard: Average number of plots per shard
            - single_shard_insecurity_prob: Probability one shard becomes insecure
            - system_insecurity_prob: Upper bound on system compromise probability
            - security_bound_alpha: The alpha threshold used
            - meets_security_bound: Whether system meets security requirements
            - security_margin: Safety margin (0.5 - p)
    """
    # Input validation
    if total_plots <= 0 or num_shards <= 0:
        raise ValueError("total_plots and num_shards must be positive")
    if not (0 <= p <= 1):
        raise ValueError(f"Malicious proportion p must be between 0 and 1, got {p}")
    if alpha <= 0:
        raise ValueError("Alpha must be positive")

    # Calculate average plots per shard (assuming equal distribution)
    n = total_plots / num_shards

    # Calculate probability that any single shard becomes insecure
    single_shard_insecurity = calculate_shard_insecurity_probability(n, p)

    # Apply union bound: P(any shard insecure) ≤ sum of individual probabilities
    # This is conservative but provides a safe upper bound
    system_insecurity = num_shards * single_shard_insecurity

    # Check if system meets the specified security bound
    meets_security_bound = system_insecurity < alpha

    return {
        "avg_plots_per_shard": n,
        "single_shard_insecurity_prob": single_shard_insecurity,
        "system_insecurity_prob": system_insecurity,
        "security_bound_alpha": alpha,
        "meets_security_bound": meets_security_bound,
        "security_margin": 0.5 - p,  # How much below 50% we are
    }


def find_maximum_tolerable_malicious_proportion(
    total_plots, num_shards, alpha=1e-6, precision=0.001
):
    """
    Find the maximum global malicious proportion the system can tolerate.
    
    THEORETICAL PURPOSE:
    This function determines the "security threshold" - the maximum percentage of
    malicious plots the ENTIRE SYSTEM can have while still maintaining shard security.
    
    METHOD:
    Uses binary search to find the largest value of p such that:
    S * e^(-n(0.5-p)²/(3p)) < α
    
    PRACTICAL SIGNIFICANCE:
    - If actual malicious proportion exceeds this threshold, shards become vulnerable
    - This helps determine system capacity limits
    - Critical for network design and security analysis
    
    EXAMPLE INTERPRETATION:
    If result is 0.35 (35%), the system can tolerate up to 35% malicious plots
    globally while keeping individual shards secure with high probability.

    Args:
        total_plots (int): Total plots across all shards
        num_shards (int): Number of shards in the system  
        alpha (float): Maximum acceptable system compromise probability
        precision (float): Binary search precision for the result

    Returns:
        float: Maximum tolerable global malicious proportion (as decimal, e.g., 0.35 = 35%)
        
    Note:
        The theoretical maximum is always < 0.5 since 50%+ global malicious 
        proportion would compromise the beacon chain itself.
    """
    # Input validation
    if total_plots <= 0 or num_shards <= 0:
        raise ValueError("total_plots and num_shards must be positive")
    if alpha <= 0:
        raise ValueError("Alpha must be positive")
    if precision <= 0 or precision >= 0.5:
        raise ValueError("Precision must be between 0 and 0.5")

    # Binary search bounds: minimum 0%, maximum 50% (beacon chain security limit)
    low, high = 0.0, 0.5

    # Binary search to find maximum tolerable proportion
    while high - low > precision:
        mid = (low + high) / 2
        
        # Test if this proportion meets security requirements
        security_result = calculate_system_security_bound(
            total_plots, num_shards, mid, alpha
        )

        if security_result["meets_security_bound"]:
            # This proportion is safe, try higher
            low = mid
        else:
            # This proportion is too risky, try lower
            high = mid

    return low


def calculate_fraud_detection_security(
    num_shards, p, n, alpha_fraud=1e-9, max_reshuffles=20
):
    """
    Analyze fraud detection capabilities through reshuffling mechanism.
    
    THEORETICAL MODEL:
    Assumes that if a shard is compromised in interval i, the fraud will be
    detected by interval i+1 through reshuffling. The model calculates:
    P(fraud undetected for k intervals) = S * (p^n)^k < α_fraud
    
    KEY ASSUMPTIONS:
    1. Perfect fraud detection after one reshuffling period
    2. Independent reshuffling events
    3. Malicious plots are randomly redistributed (no targeting)
    
    INTERPRETATION GUIDE:
    - "min_reshuffles_for_security": How many reshuffle periods needed for detection
    - "prob_detection_per_interval": Probability fraud is caught in single period
    - Lower values indicate better fraud detection capability
    
    POTENTIAL THEORETICAL ISSUE:
    The assumption p^n (probability all n plots in a shard are malicious) may be
    overly optimistic if malicious actors can coordinate or target specific shards.

    Args:
        num_shards (int): Number of shards in the system
        p (float): Global proportion of malicious plots  
        n (float): Average number of plots per shard
        alpha_fraud (float): Maximum acceptable probability of undetected fraud
        max_reshuffles (int): Maximum reshuffles to consider in analysis

    Returns:
        dict: Dictionary containing:
            - prob_detection_per_interval: Probability of detecting fraud per interval
            - prob_undetected_per_interval: Probability fraud goes undetected per interval  
            - min_reshuffles_for_security: Minimum reshuffles needed for security
            - alpha_fraud: The fraud detection threshold used
    """
    # Input validation
    if num_shards <= 0 or n <= 0:
        raise ValueError("num_shards and n must be positive")
    if not (0 <= p <= 1):
        raise ValueError(f"Malicious proportion p must be between 0 and 1, got {p}")
    if alpha_fraud <= 0:
        raise ValueError("alpha_fraud must be positive")

    # Probability that fraud is detected in one reshuffling interval
    # Detection occurs when NOT all plots assigned to a shard are malicious
    # P(fraud detected) = 1 - P(all n plots assigned are malicious) = 1 - p^n
    prob_detection_per_interval = 1 - (p**n)

    # Initialize search for minimum reshuffles needed
    min_reshuffles_needed = float("inf")

    # MATHEMATICAL APPROACH: Solve S * (p^n)^k < alpha_fraud
    if 0 < p < 1:  # Valid probability range for calculation
        prob_undetected_single_interval = p**n
        
        if prob_undetected_single_interval > 0:
            try:
                # Solve: S * (p^n)^k < alpha_fraud
                # Taking log: log(S) + k*log(p^n) < log(alpha_fraud)  
                # Therefore: k > (log(alpha_fraud) - log(S)) / log(p^n)
                k_exact = math.log(alpha_fraud / num_shards) / math.log(
                    prob_undetected_single_interval
                )
                
                if k_exact > 0:
                    min_reshuffles_needed = math.ceil(k_exact)
                elif k_exact <= 0:
                    # Already secure with single reshuffle
                    min_reshuffles_needed = 1
                    
            except (ValueError, ZeroDivisionError):
                # Handle edge cases in logarithm calculation
                pass

    # VERIFICATION APPROACH: Check each possible number of reshuffles
    if min_reshuffles_needed == float("inf"):
        for k in range(1, max_reshuffles + 1):
            # Probability fraud remains undetected after k intervals
            prob_undetected_after_k = (p**n) ** k
            
            # Apply union bound across all shards
            prob_any_fraud_undetected = num_shards * prob_undetected_after_k

            if prob_any_fraud_undetected < alpha_fraud:
                min_reshuffles_needed = k
                break

    return {
        "prob_detection_per_interval": prob_detection_per_interval,
        "prob_undetected_per_interval": p**n,
        "min_reshuffles_for_security": min_reshuffles_needed,
        "alpha_fraud": alpha_fraud,
    }


def calculate_plotting_attack_during_reshuffle(
    total_network_storage_pib,
    plotting_throughput_tib_hr_per_entity,
    max_plot_size_gib,
    reshuffle_interval_hours,
    num_shards,
    plots_per_shard,
):
    """
    Analyze whether a single malicious entity can gain shard control through plotting.
    
    ATTACK SCENARIO:
    A malicious entity uses their plotting capability during a reshuffle interval
    to create as many new plots as possible, then attempts to gain majority control
    of one or more shards through either:
    1. Random allocation (plots randomly distributed to shards)
    2. Perfect targeting (hypothetical scenario where attacker can choose shards)
    
    THEORETICAL ASSUMPTIONS:
    - Attacker starts with zero existing plots (worst-case analysis)
    - Attacker has fixed plotting throughput capacity
    - Plot allocation to shards is random (key assumption)
    - Attacker cannot coordinate with existing malicious plots
    
    CRITICAL LIMITATION:
    This model assumes random allocation, but real attackers might find ways to
    bias allocation toward specific shards, making attacks more successful than
    predicted by this analysis.
    
    INTERPRETATION GUIDE:
    - "attack_definitely_succeeds": Deterministic success (enough plots for majority)
    - "attack_likely_succeeds": >10% probability of success  
    - "prob_majority_in_any_shard": Probability of compromising at least one shard
    - "max_shards_with_perfect_targeting": Upper bound on damage with perfect targeting

    Args:
        total_network_storage_pib (float): Current total network storage in PiB
        plotting_throughput_tib_hr_per_entity (float): Plotting rate per entity (TiB/hour)
        max_plot_size_gib (float): Maximum size of individual plot in GiB  
        reshuffle_interval_hours (float): Time between reshuffles in hours
        num_shards (int): Number of shards in the system
        plots_per_shard (float): Current average plots per shard

    Returns:
        dict: Comprehensive attack analysis including:
            - Attacker capabilities and storage impact
            - Attack target requirements  
            - Success probability analysis
            - System security assessment
    """
    # Input validation
    if any(x <= 0 for x in [total_network_storage_pib, plotting_throughput_tib_hr_per_entity, 
                           max_plot_size_gib, reshuffle_interval_hours, num_shards, plots_per_shard]):
        raise ValueError("All input parameters must be positive")

    # UNIT CONVERSIONS
    # Convert PiB to GiB: 1 PiB = 1024 * 1024 GiB  
    total_network_storage_gib = total_network_storage_pib * 1024 * 1024
    # Convert TiB/hr to GiB/hr: 1 TiB = 1024 GiB
    plotting_throughput_gib_hr = plotting_throughput_tib_hr_per_entity * 1024

    # BASELINE SYSTEM STATE
    total_plots = math.floor(total_network_storage_gib / max_plot_size_gib)
    
    # TARGET ANALYSIS: What does attacker need to succeed?
    # Need >50% of shard storage to gain majority control
    plots_for_shard_majority = math.ceil(plots_per_shard * 0.51)

    # ATTACKER CAPABILITY ANALYSIS
    # How many plots can attacker create during reshuffle interval?
    attacker_new_plots_in_interval = math.floor(
        plotting_throughput_gib_hr * reshuffle_interval_hours / max_plot_size_gib
    )
    # Assume attacker starts fresh (conservative analysis)
    attacker_total_plots = attacker_new_plots_in_interval

    # ATTACK SUCCESS SCENARIOS
    
    # SCENARIO 1: Deterministic Analysis
    # Does attacker definitely have enough plots for shard majority?
    attack_definitely_succeeds = attacker_total_plots >= plots_for_shard_majority

    # SCENARIO 2: Random Allocation to Specific Target Shard
    # Probability that attacker's plots randomly concentrate in one specific shard
    prob_attacker_majority_in_specific_shard = 0.0
    if attacker_total_plots >= plots_for_shard_majority:
        try:
            # Use binomial distribution: 
            # P(≥ plots_for_shard_majority plots land in target shard)
            prob_attacker_majority_in_specific_shard = binom.sf(
                plots_for_shard_majority - 1,  # At least plots_for_shard_majority
                attacker_total_plots,          # Total attacker plots (trials)
                1.0 / num_shards,             # Probability per plot lands in target shard
            )
        except (ValueError, OverflowError):
            prob_attacker_majority_in_specific_shard = 0.0

    # SCENARIO 3: Random Allocation to ANY Shard
    # Probability that attacker gains majority in at least one shard
    prob_attacker_majority_in_any_shard = 0.0
    if attacker_total_plots >= plots_for_shard_majority:
        try:
            # For each shard independently, calculate majority probability
            prob_majority_single_shard = binom.sf(
                plots_for_shard_majority - 1, 
                attacker_total_plots, 
                1.0 / num_shards
            )
            
            # Probability of compromising at least one shard:
            # P(at least one) = 1 - P(none compromised)
            prob_no_shard_compromised = (1 - prob_majority_single_shard) ** num_shards
            prob_attacker_majority_in_any_shard = 1 - prob_no_shard_compromised
            
        except (ValueError, OverflowError):
            prob_attacker_majority_in_any_shard = 0.0

    # SCENARIO 4: Expected Damage Analysis
    # Expected number of shards attacker could compromise
    expected_shards_compromised = 0.0
    if attacker_total_plots >= plots_for_shard_majority:
        try:
            prob_majority_single_shard = binom.sf(
                plots_for_shard_majority - 1, 
                attacker_total_plots, 
                1.0 / num_shards
            )
            # Linearity of expectation
            expected_shards_compromised = num_shards * prob_majority_single_shard
        except (ValueError, OverflowError):
            expected_shards_compromised = 0.0

    # SCENARIO 5: Perfect Targeting (Upper Bound)
    # If attacker could perfectly choose which shards to target
    max_shards_with_perfect_targeting = (
        min(num_shards, attacker_total_plots // plots_for_shard_majority)
        if plots_for_shard_majority > 0 else 0
    )

    # ATTACK ASSESSMENT
    # Define success thresholds
    attack_likely_succeeds = prob_attacker_majority_in_any_shard > 0.1  # >10% chance

    # SYSTEM IMPACT ANALYSIS
    # Calculate storage impact of attack
    attacker_storage_after_plotting = attacker_total_plots * max_plot_size_gib
    total_storage_after_plotting = total_network_storage_gib + (
        attacker_new_plots_in_interval * max_plot_size_gib
    )
    attacker_network_percentage = (
        attacker_storage_after_plotting / total_storage_after_plotting
    )
    
    # Beacon chain remains secure if attacker has <50% of total network storage
    beacon_chain_secure = attacker_network_percentage < 0.5

    return {
        # Attacker Profile
        "attacker_new_plots_in_interval": attacker_new_plots_in_interval,
        "attacker_total_plots": attacker_total_plots,
        "attacker_storage_percentage_after": attacker_network_percentage,
        
        # Attack Target Requirements
        "plots_for_shard_majority": plots_for_shard_majority,
        "plots_per_shard": plots_per_shard,
        
        # Attack Success Analysis
        "attacker_can_gain_shard_majority": attack_definitely_succeeds,
        "prob_majority_in_specific_shard": prob_attacker_majority_in_specific_shard,
        "prob_majority_in_any_shard": prob_attacker_majority_in_any_shard,
        "expected_shards_compromised": expected_shards_compromised,
        "max_shards_with_perfect_targeting": max_shards_with_perfect_targeting,
        
        # Attack Assessment Summary
        "attack_definitely_succeeds": attack_definitely_succeeds,
        "attack_likely_succeeds": attack_likely_succeeds,
        "beacon_chain_secure_after_attack": beacon_chain_secure,
        
        # System State Information
        "total_plots_before": total_plots,
        "total_plots_after": total_plots + attacker_new_plots_in_interval,
    }


def calculate_finality_delay(
    min_reshuffles, reshuffle_interval_hours, beacon_block_time_seconds
):
    """
    Calculate blockchain finality delay based on fraud detection requirements.
    
    FINALITY CONCEPT:
    In this sharded system, true finality requires waiting long enough for fraud
    detection mechanisms to work. Since fraud detection relies on reshuffling,
    finality delay = (min reshuffles needed) × (reshuffle interval)
    
    PRACTICAL IMPLICATIONS:
    - Higher finality delays reduce user experience
    - Delays >24 hours are generally considered impractical for most applications
    - This creates a trade-off between security and usability
    
    THEORETICAL NOTE:
    This assumes fraud detection is perfect after the specified number of reshuffles,
    which may be optimistic in practice.

    Args:
        min_reshuffles (float): Minimum reshuffles needed for fraud detection security
        reshuffle_interval_hours (float): Hours between reshuffles
        beacon_block_time_seconds (float): Time between beacon chain blocks

    Returns:
        dict: Finality analysis containing:
            - finality_delay_hours: Total time to finality in hours
            - finality_delay_blocks: Finality delay measured in beacon blocks  
            - finality_feasible: Whether delay is practical (<24 hours)
    """
    # Handle infinite reshuffles case (impossible fraud detection)
    if min_reshuffles == float("inf"):
        return {
            "finality_delay_hours": float("inf"),
            "finality_delay_blocks": float("inf"),
            "finality_feasible": False,
        }

    # Calculate finality delay
    finality_delay_hours = min_reshuffles * reshuffle_interval_hours
    finality_delay_blocks = int(finality_delay_hours * 3600 / beacon_block_time_seconds)

    # Consider delays >24 hours as impractical
    finality_feasible = finality_delay_hours < 24

    return {
        "finality_delay_hours": finality_delay_hours,
        "finality_delay_blocks": finality_delay_blocks,
        "finality_feasible": finality_feasible,
    }


def evaluate_scenario(
    num_shards,
    max_plot_size_gib,
    total_network_storage_pib,
    plotting_throughput_tib_hr_per_entity,
    cost_per_plot_usd,
    target_reshuffle_interval_hours=1,
    avg_block_time_seconds=5,
    avg_block_size_mb=1,
    system_security_alpha=1e-6,
    fraud_detection_alpha=1e-9,
    assumed_malicious_proportion=0.3,
):
    """
    Comprehensive security evaluation of a sharded blockchain scenario.
    
    WHAT THIS FUNCTION DOES:
    Analyzes a specific blockchain configuration across multiple security dimensions:
    1. System Security: Can the system tolerate the assumed malicious proportion?
    2. Fraud Detection: How long does it take to detect fraud with high confidence?
    3. Plotting Attacks: Can individual entities compromise shards during reshuffling?
    4. Finality: How long must users wait for transaction finality?
    5. Operational Feasibility: Is the system practical to run?
    
    CRITICAL SECURITY PARAMETERS:
    - system_security_alpha: Maximum acceptable probability of ANY shard compromise
    - fraud_detection_alpha: Maximum acceptable probability of undetected fraud
    - assumed_malicious_proportion: Expected percentage of malicious plots globally
    
    HOW TO INTERPRET RESULTS:
    - "Overall Security Status": Summary of all security issues found
    - "Max Tolerable Malicious %": Security threshold for the system
    - "Finality Feasible": Whether users can practically wait for finality
    - "Attack Definitely Succeeds": Whether single entities can compromise shards
    
    Args:
        num_shards (int): Number of shards in the blockchain
        max_plot_size_gib (float): Maximum size of individual plots in GiB
        total_network_storage_pib (float): Total network storage capacity in PiB
        plotting_throughput_tib_hr_per_entity (float): Plotting rate per entity (TiB/hour)
        cost_per_plot_usd (float): Economic cost to create one plot in USD
        target_reshuffle_interval_hours (float): Time between plot reshuffles
        avg_block_time_seconds (float): Average time between beacon chain blocks
        avg_block_size_mb (float): Average block size in MB
        system_security_alpha (float): Max acceptable system compromise probability
        fraud_detection_alpha (float): Max acceptable undetected fraud probability  
        assumed_malicious_proportion (float): Assumed global malicious plot percentage

    Returns:
        dict: Comprehensive analysis results organized by category:
            - Basic System Parameters
            - Core Security Metrics  
            - System Security Bound Analysis
            - Fraud Detection Analysis
            - Finality Analysis
            - Plotting Attack Analysis
            - Operational Parameters
            - Economic Analysis
    """
    # Convert PiB to GiB
    total_network_storage_gib = total_network_storage_pib * 1024 * 1024

    # Calculate basic parameters
    target_storage_per_shard_gib = total_network_storage_gib / num_shards
    plots_per_shard_capacity = math.floor(
        target_storage_per_shard_gib / max_plot_size_gib
    )
    if plots_per_shard_capacity == 0:
        plots_per_shard_capacity = 1

    # Total plots in the system
    total_plots = math.floor(total_network_storage_gib / max_plot_size_gib)

    # 1. SYSTEM SECURITY BOUND ANALYSIS
    # Find maximum tolerable malicious proportion in the ENTIRE SYSTEM
    max_tolerable_malicious_proportion = find_maximum_tolerable_malicious_proportion(
        total_plots, num_shards, system_security_alpha
    )

    # Check if current assumption exceeds system tolerance
    system_security = calculate_system_security_bound(
        total_plots, num_shards, assumed_malicious_proportion, system_security_alpha
    )

    # 2. FRAUD DETECTION SECURITY ANALYSIS
    # Based on reshuffling model: P(fraud undetected for k intervals) = S * (p^n)^k
    fraud_detection = calculate_fraud_detection_security(
        num_shards,
        assumed_malicious_proportion,
        plots_per_shard_capacity,
        fraud_detection_alpha,
    )

    # 3. FINALITY DELAY ANALYSIS
    finality_analysis = calculate_finality_delay(
        fraud_detection["min_reshuffles_for_security"],
        target_reshuffle_interval_hours,
        avg_block_time_seconds,
    )

    # 4. PLOTTING ATTACK DURING RESHUFFLE ANALYSIS
    # Can a single malicious entity plot enough during reshuffle to gain shard majority?
    plotting_attack = calculate_plotting_attack_during_reshuffle(
        total_network_storage_pib,
        plotting_throughput_tib_hr_per_entity,
        max_plot_size_gib,
        target_reshuffle_interval_hours,
        num_shards,
        plots_per_shard_capacity,
    )

    # Cost of Reshuffling
    blocks_per_shard_per_hour = (
        target_reshuffle_interval_hours * 3600
    ) / avg_block_time_seconds
    data_to_sync_per_shard_per_hour_gb = (
        blocks_per_shard_per_hour * avg_block_size_mb
    ) / 1024

    # Qualitative Assessments
    sync_feasibility = "Manageable"
    if data_to_sync_per_shard_per_hour_gb > 10:
        sync_feasibility = "Demanding"
    elif data_to_sync_per_shard_per_hour_gb > 25:
        sync_feasibility = "Very Demanding"

    # Security Status Assessment
    security_issues = []

    # Check beacon chain security (malicious proportion must be < 50%)
    if assumed_malicious_proportion >= 0.5:
        security_issues.append("Beacon Chain Compromised")

    # Check if malicious proportion exceeds what system can tolerate for shard security
    if assumed_malicious_proportion > max_tolerable_malicious_proportion:
        security_issues.append("Exceeds Shard Security Tolerance")

    # Check system security bound
    if not system_security["meets_security_bound"]:
        security_issues.append("System Security Bound Violated")

    # Check fraud detection feasibility
    if fraud_detection["min_reshuffles_for_security"] == float("inf"):
        security_issues.append("Fraud Detection Impossible")

    # Check finality delay practicality
    if not finality_analysis["finality_feasible"]:
        security_issues.append("Impractical Finality Delay")

    # Check if single entity can gain shard majority through plotting
    if plotting_attack["attacker_can_gain_shard_majority"]:
        security_issues.append("Single Entity Can Gain Shard Majority")

    # Check if attack likely succeeds (>10% probability)
    if plotting_attack["attack_likely_succeeds"]:
        security_issues.append("High Probability Attack Success")

    # Check if attack definitely succeeds
    if plotting_attack["attack_definitely_succeeds"]:
        security_issues.append("Attack Definitely Succeeds")

    # Check if plotting causes beacon chain compromise
    if not plotting_attack["beacon_chain_secure_after_attack"]:
        security_issues.append("Plotting Compromises Beacon Chain")

    overall_security_status = (
        "Secure" if not security_issues else f"Insecure ({', '.join(security_issues)})"
    )

    return {
        # Basic System Parameters
        "N (Shards)": num_shards,
        "Net Storage (PiB)": total_network_storage_pib,
        "Plot Size (GiB)": max_plot_size_gib,
        "Total Plots": f"{total_plots:,.0f}",
        "Plots/Shard": f"{plots_per_shard_capacity:.0f}",
        # CORE SECURITY METRICS
        "Assumed Malicious %": f"{assumed_malicious_proportion:.1%}",
        "Max Tolerable Malicious %": f"{max_tolerable_malicious_proportion:.1%}",
        "Beacon Chain Security": "Secure"
        if assumed_malicious_proportion < 0.5
        else "Compromised",
        "Overall Security Status": overall_security_status,
        # System Security Bound Analysis
        "System Security Status": "Secure"
        if system_security["meets_security_bound"]
        else "Violated",
        "System Insecurity Prob.": f"{system_security['system_insecurity_prob']:.2e}",
        "Single Shard Insecurity": f"{system_security['single_shard_insecurity_prob']:.2e}",
        "Security Margin": f"{system_security['security_margin']:.3f}",
        # Fraud Detection Analysis
        "Min Reshuffles for Security": fraud_detection["min_reshuffles_for_security"]
        if fraud_detection["min_reshuffles_for_security"] != float("inf")
        else "∞",
        "Fraud Detection Prob./Interval": f"{fraud_detection['prob_detection_per_interval']:.4f}",
        "Fraud Undetected Prob./Interval": f"{fraud_detection['prob_undetected_per_interval']:.4f}",
        # Finality Analysis
        "Finality Delay (hours)": f"{finality_analysis['finality_delay_hours']:.1f}"
        if finality_analysis["finality_delay_hours"] != float("inf")
        else "∞",
        "Finality Delay (blocks)": f"{finality_analysis['finality_delay_blocks']:,.0f}"
        if finality_analysis["finality_delay_blocks"] != float("inf")
        else "∞",
        "Finality Feasible": "Yes" if finality_analysis["finality_feasible"] else "No",
        # Single Entity Plotting Attack Analysis
        "Attacker New Plots in Interval": plotting_attack[
            "attacker_new_plots_in_interval"
        ],
        "Attacker Total Plots": f"{plotting_attack['attacker_total_plots']:,.0f}",
        "Attacker Storage % After": f"{plotting_attack['attacker_storage_percentage_after']:.1%}",
        "Plots for Shard Majority": plotting_attack["plots_for_shard_majority"],
        "Beacon Secure After Attack": "Yes"
        if plotting_attack["beacon_chain_secure_after_attack"]
        else "No",
        "Max Shards w/ Perfect Targeting": plotting_attack[
            "max_shards_with_perfect_targeting"
        ],
        # # Attack Success Analysis
        # "Can Gain Shard Majority": "Yes" if plotting_attack['attacker_can_gain_shard_majority'] else "No",
        # "Prob. Majority in Specific Shard": f"{plotting_attack['prob_majority_in_specific_shard']:.2e}",
        # "Prob. Majority in Any Shard": f"{plotting_attack['prob_majority_in_any_shard']:.2e}",
        # "Expected Shards Compromised": f"{plotting_attack['expected_shards_compromised']:.2f}",
        # "Attack Definitely Succeeds": "Yes" if plotting_attack['attack_definitely_succeeds'] else "No",
        # "Attack Likely Succeeds": "Yes" if plotting_attack['attack_likely_succeeds'] else "No",
        # Operational Parameters
        "Reshuffle Interval (hrs)": target_reshuffle_interval_hours,
        "Sync Data (GB/hr)": f"{data_to_sync_per_shard_per_hour_gb:.2f}",
        "Sync Feasibility": sync_feasibility,
        # Economic
        "Base Plot Cost (USD)": f"${cost_per_plot_usd:.2f}",
        "Honest Shard Cost (USD)": f"${plots_per_shard_capacity * cost_per_plot_usd:,.0f}",
        "Plotting Attack Cost (USD)": f"${plotting_attack['attacker_total_plots'] * cost_per_plot_usd:,.0f}",
    }


# Test scenarios using plot-based model
scenarios = [
    {
        "name": "Conservative: 25% Malicious",
        "num_shards": 10,
        "max_plot_size_gib": 64000,
        "total_network_storage_pib": 500,
        "plotting_throughput_tib_hr_per_entity": 10000,
        "cost_per_plot_usd": 5.3,  # TODO: Instead of having this per plot have this per GB so that it is easier to reason and we can then multiply by plot size.
        "target_reshuffle_interval_hours": 1,
        "assumed_malicious_proportion": 0.332,
        "system_security_alpha": 1e-9,
        "fraud_detection_alpha": 1e-12,
    },
    {
        "name": "Moderate: 35% Malicious",
        "num_shards": 3,
        "max_plot_size_gib": 64000,
        "total_network_storage_pib": 500,
        "plotting_throughput_tib_hr_per_entity": 100,
        "cost_per_plot_usd": 0.25,
        "target_reshuffle_interval_hours": 1,
        "assumed_malicious_proportion": 0.35,
        "system_security_alpha": 1e-6,
        "fraud_detection_alpha": 1e-9,
    },
    {
        "name": "High Shards: 100 Shards",
        "num_shards": 100,
        "max_plot_size_gib": 100,
        "total_network_storage_pib": 500,
        "plotting_throughput_tib_hr_per_entity": 10,
        "cost_per_plot_usd": 0.25,
        "target_reshuffle_interval_hours": 1,
        "assumed_malicious_proportion": 0.3,
        "system_security_alpha": 1e-6,
        "fraud_detection_alpha": 1e-9,
    },
    {
        "name": "45% Malicious",
        "num_shards": 50,
        "max_plot_size_gib": 100,
        "total_network_storage_pib": 200,
        "plotting_throughput_tib_hr_per_entity": 50,
        "cost_per_plot_usd": 0.25,
        "target_reshuffle_interval_hours": 1,
        "assumed_malicious_proportion": 0.45,
        "system_security_alpha": 1e-6,
        "fraud_detection_alpha": 1e-9,
    },
    {
        "name": "ATTACK SUCCESS: Fast Plotting Small Shards",
        "num_shards": 100,  # Many small shards
        "max_plot_size_gib": 100,  # Small plots
        "total_network_storage_pib": 50,  # Smaller network
        "plotting_throughput_tib_hr_per_entity": 5000,  # Very high plotting throughput
        "cost_per_plot_usd": 0.10,  # Cheaper plots
        "target_reshuffle_interval_hours": 1,  # Longer interval gives attacker more time
        "assumed_malicious_proportion": 0.2,  # Lower background malicious proportion
        "system_security_alpha": 1e-6,
        "fraud_detection_alpha": 1e-9,
    },
]


def main():
    scenario_results = []
    scenario_names = []

    for scenario_params in scenarios:
        scenario_name = scenario_params.pop("name")
        scenario_names.append(scenario_name)

        row_data = evaluate_scenario(**scenario_params)
        scenario_results.append(row_data)

    table = PrettyTable()
    table.field_names = ["Parameter"] + scenario_names
    table.align = "l"

    for _ in scenario_names:
        table.align[_] = "c"

    # Define parameter sections
    parameter_sections = [
        {
            "title": "=== BASIC SYSTEM PARAMETERS ===",
            "fields": [
                "N (Shards)",
                "Net Storage (PiB)",
                "Plot Size (GiB)",
                "Total Plots",
                "Plots/Shard",
            ],
        },
        {
            "title": "=== CORE SECURITY ANALYSIS ===",
            "fields": [
                "Assumed Malicious %",
                "Max Tolerable Malicious %",
                "Beacon Chain Security",
                "Overall Security Status",
            ],
        },
        {
            "title": "=== SYSTEM SECURITY BOUND ===",
            "fields": [
                "System Security Status",
                "System Insecurity Prob.",
                "Single Shard Insecurity",
                "Security Margin",
            ],
        },
        {
            "title": "=== FRAUD DETECTION ANALYSIS ===",
            "fields": [
                "Min Reshuffles for Security",
                "Fraud Detection Prob./Interval",
                "Fraud Undetected Prob./Interval",
            ],
        },
        {
            "title": "=== FINALITY ANALYSIS ===",
            "fields": [
                "Finality Delay (hours)",
                "Finality Delay (blocks)",
                "Finality Feasible",
            ],
        },
        {
            "title": "=== PLOTTING ATTACK ANALYSIS ===",
            "fields": [
                "Attacker New Plots in Interval",
                "Attacker Total Plots",
                "Attacker Storage % After",
                "Plots for Shard Majority",
                "Beacon Secure After Attack",
                "Max Shards w/ Perfect Targeting",
            ],
        },
        # {
        #     "title": "=== ATTACK SUCCESS ANALYSIS ===",
        #     "fields": ["Can Gain Shard Majority", "Prob. Majority in Specific Shard", "Prob. Majority in Any Shard",
        #               "Expected Shards Compromised", "Max Shards w/ Perfect Targeting",
        #               "Attack Definitely Succeeds", "Attack Likely Succeeds", ]
        # },
        {
            "title": "=== OPERATIONAL PARAMETERS ===",
            "fields": [
                "Reshuffle Interval (hrs)",
                "Sync Data (GB/hr)",
                "Sync Feasibility",
            ],
        },
        {
            "title": "=== ECONOMIC ANALYSIS ===",
            "fields": [
                "Base Plot Cost (USD)",
                "Honest Shard Cost (USD)",
                "Plotting Attack Cost (USD)",
            ],
        },
    ]

    # Add rows with section headers
    for section in parameter_sections:
        # Add section header row
        header_row = [section["title"]] + [""] * len(scenario_names)
        table.add_row(header_row)

        # Add parameter rows for this section
        for field in section["fields"]:
            row_values = [field]
            for result_dict in scenario_results:
                row_values.append(result_dict.get(field, "N/A"))
            table.add_row(row_values)

    print("=== PLOT-BASED SHARDED BLOCKCHAIN SECURITY ANALYSIS ===")
    print()
    print("This analysis uses PLOTS as the fundamental unit (no farmers concept):")
    print("1. SYSTEM SECURITY BOUND: P(System Insecure) ≤ S * e^(-n(0.5-p)²/(3p)) < α")
    print(
        "2. FRAUD DETECTION: P(fraud undetected for k intervals) = S * (p^n)^k < α_fraud"
    )
    print(
        "3. PLOTTING ATTACK: Can entities plot enough during reshuffle to gain shard majority?"
    )
    print()
    print("=" * 80)
    print("HOW TO INTERPRET THE RESULTS:")
    print("=" * 80)
    print()
    print("🔒 SECURITY STATUS INDICATORS:")
    print("• 'Secure' = All security conditions are met")
    print("• 'Insecure' = One or more security conditions violated (details in parentheses)")
    print()
    print("📊 KEY METRICS TO FOCUS ON:")
    print("• Max Tolerable Malicious %: System's security threshold")
    print("  - If 'Assumed Malicious %' > this value → System is vulnerable")
    print("• Overall Security Status: Summary of all security issues")
    print("• Finality Feasible: Whether users can wait for transaction finality")
    print("• Attack Definitely Succeeds: Whether single entities can compromise shards")
    print()
    print("⚠️  SECURITY WARNINGS TO WATCH FOR:")
    print("• 'Exceeds Shard Security Tolerance' = Too many malicious plots globally")
    print("• 'Single Entity Can Gain Shard Majority' = Plotting attacks succeed")
    print("• 'Impractical Finality Delay' = Users must wait too long for finality")
    print("• 'Beacon Chain Compromised' = >50% malicious plots globally")
    print()
    print("💰 ECONOMIC INTERPRETATION:")
    print("• Base Plot Cost: Cost for honest entities to create plots")  
    print("• Plotting Attack Cost: Cost for malicious entity to attempt shard takeover")
    print("• Lower attack costs relative to honest costs indicate vulnerability")
    print()
    print("🔄 OPERATIONAL PARAMETERS:")
    print("• Reshuffle Interval: How often plots are redistributed")
    print("• Sync Data: Amount of data nodes must sync during reshuffles")
    print("• 'Very Demanding' sync feasibility may indicate operational issues")
    print()
    print("=" * 80)
    print("THEORETICAL LIMITATIONS & POTENTIAL ISSUES:")
    print("=" * 80)
    print()
    print("⚠️  CRITICAL ASSUMPTIONS THAT MAY NOT HOLD:")
    print()
    print("1. RANDOM ALLOCATION ASSUMPTION:")
    print("   • Analysis assumes plot allocation to shards is truly random")
    print("   • Real attackers might find ways to bias allocation toward target shards")
    print("   • This could make attacks more successful than predicted")
    print()
    print("2. INDEPENDENCE ASSUMPTION:")
    print("   • Assumes plot creation by different entities is independent")
    print("   • Coordinated attacks by multiple entities can be modelled as a single big entity")
    print()
    print("3. PERFECT FRAUD DETECTION:")
    print("   • Assumes fraud is detected perfectly after reshuffling")
    print("   • Real detection may be delayed or incomplete")
    print("   • Sophisticated attacks might evade detection longer")
    print()
    print("4. STATIC ANALYSIS:")
    print("   • Network size and parameters assumed constant")
    print("   • Does not model dynamic growth or adaptive attacks")
    print("   • Economic conditions and incentives assumed fixed")
    print()
    print("5. SIMPLIFIED COST MODEL:")
    print("   • Only considers plotting costs, ignores operational costs")
    print("   • Does not model market dynamics or economic attacks")
    print("   • No consideration of opportunity costs or ROI")
    print()
    print("=" * 80)
    print("PARAMETER SENSITIVITY ANALYSIS:")
    print("=" * 80)
    print("To understand system robustness, vary these key parameters:")
    print("• num_shards: More shards → easier to attack individual shards")
    print("• plotting_throughput: Higher rates → more dangerous attacks")
    print("• reshuffle_interval: Longer intervals → more time for plotting attacks")
    print("• max_plot_size: Smaller plots → need more plots for majority")
    print()
    print(str(table))


if __name__ == "__main__":
    main()
