import math
from scipy.stats import binom
from prettytable import PrettyTable
import numpy as np

def calculate_attack_probability(K_M, N, k_alpha):
    """
    Calculates the probability of an attacker getting at least k_alpha plots
    in a specific shard, given their total plots K_M and total shards N.
    
    This uses the survival function (sf) of the binomial distribution, which is
    P(X >= k_alpha), where X is the number of attacker plots landing in the target shard.
    K_M is the total number of trials (attacker's plots), and 1/N is the probability
    of success (a plot landing in the target shard).
    """
    if k_alpha <= 0 or K_M <= 0 or N <= 0:
        return 0.0
    if k_alpha > K_M:
        return 0.0

    p_success = 1.0 / N
    probability = binom.sf(k_alpha - 1, K_M, p_success)
    return probability

def find_min_K_M_for_success_prob(k_alpha, N, target_prob=0.9):
    """
    Finds the minimum total plots (K_M) an attacker needs to generate
    to achieve at least k_alpha plots in a target shard with 'target_prob' certainty.
    """
    if k_alpha <= 0 or N <= 0:
        return 0
    if target_prob <= 0:
        return max(1, int(k_alpha * N * (1.0/0.51)))

    p_success_per_plot = 1.0 / N
    current_K_M = int(k_alpha * N * 1.5)
    if current_K_M == 0: 
        current_K_M = 1

    if k_alpha == 1:
        if p_success_per_plot == 1.0:
            return k_alpha
        required_K_M_for_1_plot = math.ceil(math.log(1 - target_prob) / math.log(1 - p_success_per_plot))
        current_K_M = max(current_K_M, int(required_K_M_for_1_plot))
        
    max_attempts = 2000
    step = max(1, int(current_K_M * 0.1))
    
    while calculate_attack_probability(current_K_M, N, k_alpha) < target_prob and max_attempts > 0:
        current_K_M += step
        max_attempts -= 1
        if current_K_M > 10**12: 
            return float('inf')
    
    if max_attempts == 0 and calculate_attack_probability(current_K_M, N, k_alpha) < target_prob:
        return float('inf')

    return current_K_M

def calculate_shard_insecurity_probability(n, p):
    """
    Calculate the probability that a single shard with n farmers becomes insecure
    (has >= 50% malicious farmers) using Chernoff bound.
    
    Args:
        n: Number of farmers in the shard
        p: Global proportion of malicious farmers
    
    Returns:
        Probability that the shard is insecure
    """
    if p >= 0.5:
        return 1.0  # If global malicious proportion >= 50%, shard is likely insecure
    
    # Using Chernoff bound: P(M/n >= 0.5) <= e^(-n(0.5-p)^2 / (3p))
    epsilon = 0.5 - p  # Security margin
    if epsilon <= 0:
        return 1.0
    
    exponent = -n * (epsilon ** 2) / (3 * p)
    return math.exp(exponent)

def calculate_system_security_bound(N, S, p, alpha=1e-6):
    """
    Calculate whether the system meets the security bound for all shards to be secure.
    
    Args:
        N: Total number of farmers
        S: Number of shards
        p: Proportion of malicious farmers
        alpha: Acceptable probability of system being insecure
    
    Returns:
        Dictionary with security analysis results
    """
    n = N / S  # Average farmers per shard
    
    # Probability that any single shard is insecure
    single_shard_insecurity = calculate_shard_insecurity_probability(n, p)
    
    # Probability that the entire system is insecure (union bound)
    system_insecurity = S * single_shard_insecurity
    
    # Check if system meets security bound
    meets_security_bound = system_insecurity < alpha
    
    return {
        "avg_farmers_per_shard": n,
        "single_shard_insecurity_prob": single_shard_insecurity,
        "system_insecurity_prob": system_insecurity,
        "security_bound_alpha": alpha,
        "meets_security_bound": meets_security_bound,
        "security_margin": 0.5 - p
    }

def calculate_fraud_detection_security(S, p, n, alpha_fraud=1e-9, max_reshuffles=10):
    """
    Calculate fraud detection security based on reshuffling model.
    
    Args:
        S: Number of shards
        p: Proportion of malicious farmers
        n: Average number of farmers per shard
        alpha_fraud: Acceptable probability of undetected fraud
        max_reshuffles: Maximum reshuffles to consider
    
    Returns:
        Dictionary with fraud detection analysis
    """
    # Probability that fraud is detected in one reshuffling interval
    prob_detection_per_interval = 1 - (p ** n)
    
    # Find minimum number of reshuffles needed
    min_reshuffles_needed = float('inf')
    
    for k in range(1, max_reshuffles + 1):
        # Probability that fraud remains undetected after k reshuffles
        prob_undetected_after_k = (p ** n) ** k
        
        # Probability that any fraud in any shard remains undetected
        prob_any_fraud_undetected = S * prob_undetected_after_k
        
        if prob_any_fraud_undetected < alpha_fraud:
            min_reshuffles_needed = k
            break
    
    # Calculate detection probabilities for various reshuffle counts
    detection_probs = {}
    for k in range(1, min(max_reshuffles + 1, 6)):
        prob_detected_by_k = 1 - ((p ** n) ** k)
        detection_probs[f"detected_by_reshuffle_{k}"] = prob_detected_by_k
    
    return {
        "prob_detection_per_interval": prob_detection_per_interval,
        "min_reshuffles_for_security": min_reshuffles_needed,
        "alpha_fraud": alpha_fraud,
        **detection_probs
    }

def calculate_finality_delay(min_reshuffles, reshuffle_interval_hours, beacon_block_time_seconds):
    """
    Calculate the finality delay based on reshuffling requirements.
    
    Args:
        min_reshuffles: Minimum reshuffles needed for fraud detection security
        reshuffle_interval_hours: Time between reshuffles in hours
        beacon_block_time_seconds: Beacon chain block time
    
    Returns:
        Dictionary with finality timing information
    """
    if min_reshuffles == float('inf'):
        return {
            "finality_delay_hours": float('inf'),
            "finality_delay_blocks": float('inf'),
            "finality_feasible": False
        }
    
    finality_delay_hours = min_reshuffles * reshuffle_interval_hours
    finality_delay_blocks = int(finality_delay_hours * 3600 / beacon_block_time_seconds)
    
    return {
        "finality_delay_hours": finality_delay_hours,
        "finality_delay_blocks": finality_delay_blocks,
        "finality_feasible": finality_delay_hours < 24  # Arbitrary threshold for "reasonable" finality
    }

def find_maximum_secure_malicious_proportion(N, S, alpha=1e-6, precision=0.001):
    """
    Find the maximum proportion of malicious farmers the system can tolerate
    while maintaining security.
    
    Args:
        N: Total number of farmers
        S: Number of shards
        alpha: Acceptable probability of system being insecure
        precision: Search precision for binary search
    
    Returns:
        Maximum secure proportion of malicious farmers
    """
    low, high = 0.0, 0.5
    
    while high - low > precision:
        mid = (low + high) / 2
        security_result = calculate_system_security_bound(N, S, mid, alpha)
        
        if security_result["meets_security_bound"]:
            low = mid
        else:
            high = mid
    
    return low

def evaluate_scenario(
    num_shards,
    max_plot_size_gib,
    total_network_storage_pib,
    plotting_throughput_tib_hr_per_attacker,
    attacker_storage_percentage,
    cost_per_plot_usd,
    attacker_model="storage-limited",
    target_attack_success_probability=0.9,
    control_percentage_for_shard=0.51,
    target_reshuffle_interval_hours=1,
    avg_block_time_seconds=5,
    avg_block_size_mb=1,
    # New security parameters
    system_security_alpha=1e-6,
    fraud_detection_alpha=1e-9,
    assumed_malicious_proportion=0.3
):
    """
    Enhanced scenario evaluation including both security models.
    """
    # Convert PiB to GiB for consistent calculations
    total_network_storage_gib = total_network_storage_pib * 1024 * 1024
    attacker_plotting_throughput_gib_hr = plotting_throughput_tib_hr_per_attacker * 1024

    # Shard Capacity and k_alpha
    target_storage_per_shard_gib = total_network_storage_gib / num_shards
    plots_per_shard_capacity = math.floor(target_storage_per_shard_gib / max_plot_size_gib)
    if plots_per_shard_capacity == 0:
        plots_per_shard_capacity = 1

    k_alpha = math.ceil(control_percentage_for_shard * plots_per_shard_capacity)
    if k_alpha == 0:
        k_alpha = 1

    # Total number of farmers/plots in the system
    total_farmers = math.floor(total_network_storage_gib / max_plot_size_gib)

    # No piece selection risk modeling for now
    piece_selection_cost_multiplier = 1.0

    # Attacker's Total Plots (K_M) - existing logic
    if attacker_model == "storage-limited":
        attacker_total_storage_gib = total_network_storage_gib * attacker_storage_percentage
        K_M_calculated = math.floor(attacker_total_storage_gib / max_plot_size_gib)
        attacker_model_description = f"Storage-Limited ({attacker_storage_percentage:.1%})"
    elif attacker_model == "throughput-limited":
        K_M_calculated = find_min_K_M_for_success_prob(k_alpha, num_shards, target_attack_success_probability)
        attacker_model_description = f"Throughput-Limited (Prob. {target_attack_success_probability:.1%})"
    else:
        raise ValueError("Invalid attacker_model specified.")

    K_M = max(1, K_M_calculated)

    # Existing calculations
    prob_plotting_attack = calculate_attack_probability(K_M, num_shards, k_alpha)
    plots_per_hr_per_attacker = attacker_plotting_throughput_gib_hr / max_plot_size_gib
    time_to_plot_km_hours = K_M / plots_per_hr_per_attacker if plots_per_hr_per_attacker > 0 else float('inf')
    economic_cost_of_attack_usd = K_M * cost_per_plot_usd * piece_selection_cost_multiplier
    cost_of_honest_shard_usd = plots_per_shard_capacity * cost_per_plot_usd
    honest_cost_for_attacker_storage_usd = (total_network_storage_gib * attacker_storage_percentage) / max_plot_size_gib * cost_per_plot_usd

    # New Security Analysis
    # 1. System Security Bound Analysis
    system_security = calculate_system_security_bound(
        total_farmers, num_shards, assumed_malicious_proportion, system_security_alpha
    )
    
    # 2. Find maximum tolerable malicious proportion
    max_malicious_proportion = find_maximum_secure_malicious_proportion(
        total_farmers, num_shards, system_security_alpha
    )
    
    # 3. Fraud Detection Security Analysis
    fraud_detection = calculate_fraud_detection_security(
        num_shards, assumed_malicious_proportion, plots_per_shard_capacity, fraud_detection_alpha
    )
    
    # 4. Finality Delay Analysis
    finality_analysis = calculate_finality_delay(
        fraud_detection["min_reshuffles_for_security"],
        target_reshuffle_interval_hours,
        avg_block_time_seconds
    )

    # Cost of Reshuffling (existing logic)
    blocks_per_shard_per_hour = (target_reshuffle_interval_hours * 3600) / avg_block_time_seconds
    data_to_sync_per_shard_per_hour_gb = (blocks_per_shard_per_hour * avg_block_size_mb) / 1024

    # Qualitative Assessments (existing logic with some updates)
    plotting_attack_risk = "Low (Time to plot >> Reshuffle)"
    if time_to_plot_km_hours <= target_reshuffle_interval_hours:
        plotting_attack_risk = "High (Time to plot <= Reshuffle)"
    elif time_to_plot_km_hours <= target_reshuffle_interval_hours * 24:
        plotting_attack_risk = "Medium (Time to plot ~ Day)"

    allocation_prob_risk = "Very Low"
    if prob_plotting_attack > 0.0001:
        allocation_prob_risk = "Moderate"
    if prob_plotting_attack > 0.01:
        allocation_prob_risk = "High"

    sync_feasibility = "Manageable"
    if data_to_sync_per_shard_per_hour_gb > 10:
        sync_feasibility = "Demanding"
    elif data_to_sync_per_shard_per_hour_gb > 25:
        sync_feasibility = "Very Demanding"

    economic_cost_vs_honest = ""
    if attacker_model == "storage-limited":
        if economic_cost_of_attack_usd < (honest_cost_for_attacker_storage_usd * 0.9):
            economic_cost_vs_honest = "Less than honest equivalent"
        elif economic_cost_of_attack_usd > (honest_cost_for_attacker_storage_usd * 1.1):
            economic_cost_vs_honest = "Higher than honest equivalent"
        else:
            economic_cost_vs_honest = "Comparable to honest equivalent"
    else:
        if economic_cost_of_attack_usd < (cost_of_honest_shard_usd * 0.9):
            economic_cost_vs_honest = "Less than 1 Shard Honest Cost"
        elif economic_cost_of_attack_usd > (cost_of_honest_shard_usd * 1.1):
            economic_cost_vs_honest = "Higher than 1 Shard Honest Cost"
        else:
            economic_cost_vs_honest = "Comparable to 1 Shard Honest Cost"

    min_plots_per_shard_for_security = num_shards / 1100.0
    shard_member_security_risk = "Secure (Meets Min)"
    if plots_per_shard_capacity < min_plots_per_shard_for_security:
        shard_member_security_risk = "Vulnerable (Below Min)"
    elif plots_per_shard_capacity < min_plots_per_shard_for_security * 1.5:
         shard_member_security_risk = "Borderline (Close to Min)"

    # Security Assessment
    overall_security_status = "Secure"
    if not system_security["meets_security_bound"]:
        overall_security_status = "Insecure (System Bound Violation)"
    elif fraud_detection["min_reshuffles_for_security"] == float('inf'):
        overall_security_status = "Insecure (Fraud Detection Impossible)"
    elif not finality_analysis["finality_feasible"]:
        overall_security_status = "Questionable (Long Finality Delay)"

    return {
        # Existing fields
        "Attacker Model": attacker_model_description,
        "N (Shards)": num_shards,
        "Net Storage (PiB)": total_network_storage_pib,
        "Plot Size (GiB)": max_plot_size_gib,
        "Attacker % / Target Prob.": f"{attacker_storage_percentage:.1%}" if attacker_model == "storage-limited" else f"{target_attack_success_probability:.1%}",
        "k_alpha (plots)": k_alpha,
        "K_M (plots)": f"{K_M:,.0f}",
        "Plotting Prob.": f"{prob_plotting_attack:.2e}",
        "Plot Time (days)": f"{time_to_plot_km_hours / 24:.2f}",
        "Economic Cost (USD)": f"${economic_cost_of_attack_usd:,.0f}",
        "Base Plot Cost (USD)": f"${cost_per_plot_usd:.2f}",
        "Cost vs. Honest": economic_cost_vs_honest,
        "Honest Shard Cost (USD)": f"${cost_of_honest_shard_usd:,.0f}",
        "Reshuffle (hrs)": target_reshuffle_interval_hours,
        "Sync Data (GB/hr)": f"{data_to_sync_per_shard_per_hour_gb:.2f}",
        "Plots/Shard": plots_per_shard_capacity,
        "Min Plots/Shard": f"{min_plots_per_shard_for_security:.2f}",
        "Shard Member Security": shard_member_security_risk,
        "Plot Attack Risk": plotting_attack_risk,
        "Alloc. Prob. Risk": allocation_prob_risk,
        "Sync Feasibility": sync_feasibility,
        
        # New security fields
        "Total Farmers": f"{total_farmers:,.0f}",
        "Assumed Malicious %": f"{assumed_malicious_proportion:.1%}",
        "Max Secure Malicious %": f"{max_malicious_proportion:.1%}",
        "System Security Status": "Secure" if system_security["meets_security_bound"] else "Violated",
        "System Insecurity Prob.": f"{system_security['system_insecurity_prob']:.2e}",
        "Single Shard Insecurity": f"{system_security['single_shard_insecurity_prob']:.2e}",
        "Min Reshuffles for Security": fraud_detection["min_reshuffles_for_security"] if fraud_detection["min_reshuffles_for_security"] != float('inf') else "∞",
        "Fraud Detection Prob./Interval": f"{fraud_detection['prob_detection_per_interval']:.4f}",
        "Finality Delay (hours)": f"{finality_analysis['finality_delay_hours']:.1f}" if finality_analysis['finality_delay_hours'] != float('inf') else "∞",
        "Finality Delay (blocks)": f"{finality_analysis['finality_delay_blocks']:,.0f}" if finality_analysis['finality_delay_blocks'] != float('inf') else "∞",
        "Overall Security Status": overall_security_status
    }

# Enhanced scenarios with security parameters
scenarios = [
    {
        "name": "Nazar 10 Shards - Conservative Security",
        "num_shards": 10,
        "max_plot_size_gib": 64000,
        "total_network_storage_pib": 500,
        "plotting_throughput_tib_hr_per_attacker": 1000,
        "attacker_storage_percentage": 0.5,
        "cost_per_plot_usd": 0.25,
        "attacker_model": "storage-limited",
        "target_reshuffle_interval_hours": 1,
        "assumed_malicious_proportion": 0.25,  # Conservative assumption
        "system_security_alpha": 1e-9,  # Very high security requirement
        "fraud_detection_alpha": 1e-12
    },
    {
        "name": "Nazar 3 Shards - High Throughput",
        "num_shards": 3,
        "max_plot_size_gib": 64000,
        "total_network_storage_pib": 500,
        "plotting_throughput_tib_hr_per_attacker": 1000,
        "attacker_storage_percentage": 0.5,
        "cost_per_plot_usd": 0.25,
        "attacker_model": "throughput-limited",
        "target_attack_success_probability": 0.90,
        "target_reshuffle_interval_hours": 1,
        "assumed_malicious_proportion": 0.3,
        "system_security_alpha": 1e-6,
        "fraud_detection_alpha": 1e-9
    },
    {
        "name": "Security Test - Many Shards",
        "num_shards": 100,
        "max_plot_size_gib": 100,
        "total_network_storage_pib": 500,
        "plotting_throughput_tib_hr_per_attacker": 3.6,
        "attacker_storage_percentage": 0.01,
        "cost_per_plot_usd": 0.25,
        "attacker_model": "storage-limited",
        "target_reshuffle_interval_hours": 1,
        "assumed_malicious_proportion": 0.35,
        "system_security_alpha": 1e-6,
        "fraud_detection_alpha": 1e-9
    },
   {
        "name": "High Malicious Proportion Test",
        "num_shards": 50,
        "max_plot_size_gib": 100,
        "total_network_storage_pib": 200,
        "plotting_throughput_tib_hr_per_attacker": 10,
        "attacker_storage_percentage": 0.05,
        "cost_per_plot_usd": 0.25,
        "attacker_model": "throughput-limited",
        "target_attack_success_probability": 0.95,
        "target_reshuffle_interval_hours": 2,
        "assumed_malicious_proportion": 0.45,  # High malicious proportion
        "system_security_alpha": 1e-6,
        "fraud_detection_alpha": 1e-9
    },
    {
        "name": "INSECURE: Too Many Shards",
        "num_shards": 1000,  # Way too many shards
        "max_plot_size_gib": 1000,
        "total_network_storage_pib": 100,  # Small network
        "plotting_throughput_tib_hr_per_attacker": 10,
        "attacker_storage_percentage": 0.1,
        "cost_per_plot_usd": 0.25,
        "attacker_model": "storage-limited",
        "target_reshuffle_interval_hours": 1,
        "assumed_malicious_proportion": 0.35,  # Moderate malicious proportion
        "system_security_alpha": 1e-6,
        "fraud_detection_alpha": 1e-9
    },
    {
        "name": "INSECURE: High Malicious + Many Shards",
        "num_shards": 200,
        "max_plot_size_gib": 500,
        "total_network_storage_pib": 50,  # Small network
        "plotting_throughput_tib_hr_per_attacker": 100,
        "attacker_storage_percentage": 0.2,
        "cost_per_plot_usd": 0.1,
        "attacker_model": "throughput-limited",
        "target_attack_success_probability": 0.99,
        "target_reshuffle_interval_hours": 1,
        "assumed_malicious_proportion": 0.48,  # Very high malicious proportion
        "system_security_alpha": 1e-6,
        "fraud_detection_alpha": 1e-9
    },
    {
        "name": "INSECURE: Fraud Detection Impossible",
        "num_shards": 10,
        "max_plot_size_gib": 10000,  # Large plots = few farmers per shard
        "total_network_storage_pib": 10,  # Small network
        "plotting_throughput_tib_hr_per_attacker": 50,
        "attacker_storage_percentage": 0.3,
        "cost_per_plot_usd": 0.25,
        "attacker_model": "storage-limited",
        "target_reshuffle_interval_hours": 1,
        "assumed_malicious_proportion": 0.4,  # High malicious proportion with few farmers
        "system_security_alpha": 1e-6,
        "fraud_detection_alpha": 1e-15  # Very strict fraud detection requirement
    },
    {
        "name": "EDGE CASE: Single Farmer Per Shard",
        "num_shards": 100,
        "max_plot_size_gib": 100000,  # Huge plots
        "total_network_storage_pib": 10,  # Small network = ~1 farmer per shard
        "plotting_throughput_tib_hr_per_attacker": 10,
        "attacker_storage_percentage": 0.2,
        "cost_per_plot_usd": 0.25,
        "attacker_model": "throughput-limited",
        "target_attack_success_probability": 0.9,
        "target_reshuffle_interval_hours": 1,
        "assumed_malicious_proportion": 0.3,
        "system_security_alpha": 1e-6,
        "fraud_detection_alpha": 1e-9
    }
]

def main():
    # Enhanced parameter fields including new security metrics
    parameter_fields = [
        "Attacker Model", "N (Shards)", "Net Storage (PiB)", "Plot Size (GiB)",
        "Total Farmers", "Plots/Shard", "Min Plots/Shard",
        
        # Security Analysis
        "Assumed Malicious %", "Max Secure Malicious %", "Overall Security Status",
        "System Security Status", "System Insecurity Prob.", "Single Shard Insecurity",
        
        # Fraud Detection & Finality
        "Min Reshuffles for Security", "Fraud Detection Prob./Interval", 
        "Finality Delay (hours)", "Finality Delay (blocks)",
        "Reshuffle (hrs)", "Sync Data (GB/hr)", "Sync Feasibility",
        
        # Attack Analysis
        "Attacker % / Target Prob.", "k_alpha (plots)", "K_M (plots)", 
        "Plotting Prob.", "Plot Time (days)", "Plot Attack Risk", "Alloc. Prob. Risk",
        
        # Economic Analysis
        "Economic Cost (USD)", "Honest Shard Cost (USD)", "Base Plot Cost (USD)", 
        "Cost vs. Honest",
        
        # Legacy Security
        "Shard Member Security"
    ]

    # Collect results from all scenarios
    scenario_results = []
    scenario_names = []

    for scenario_params in scenarios:
        scenario_name = scenario_params.pop("name")
        scenario_names.append(scenario_name)

        if "attacker_model" not in scenario_params:
            scenario_params["attacker_model"] = "storage-limited"
        
        row_data = evaluate_scenario(**scenario_params)
        scenario_results.append(row_data)

    # Create the pivoted table
    table = PrettyTable()
    table.field_names = ["Parameter"] + scenario_names
    table.align = "l"
    
    for _ in scenario_names:
        table.align[_] = "c"

    # Populate the table
    for field in parameter_fields:
        row_values = [field]
        for result_dict in scenario_results:
            row_values.append(result_dict.get(field, "N/A")) 
        table.add_row(row_values)

    # Print enhanced summary
    # print()
    # print("This analysis integrates two critical security models:")
    # print("1. SYSTEM SECURITY BOUND: Ensures all shards remain honest with high probability")
    # print("2. FRAUD DETECTION SECURITY: Models reshuffling-based fraud detection without fraud proofs")
    # print()
    # print("KEY SECURITY METRICS:")
    # print("• Overall Security Status: Combined assessment of system security and fraud detection feasibility")
    # print("• Max Secure Malicious %: Maximum proportion of malicious farmers the system can tolerate")
    # print("• System Security Status: Whether the system meets the Chernoff bound security requirement")
    # print("• Min Reshuffles for Security: Minimum reshuffles needed to detect fraud with high probability")
    # print("• Finality Delay: Time to achieve probabilistic finality considering fraud detection")
    # print()
    # print("SECURITY MODEL PARAMETERS:")
    # print("• System Security Alpha: Acceptable probability of any shard being insecure (default: 1e-6)")
    # print("• Fraud Detection Alpha: Acceptable probability of undetected fraud (default: 1e-9)")
    # print("• Assumed Malicious %: Assumed proportion of malicious farmers for analysis")
    # print()
    print(str(table))

    # print("  Overall Security Status:")
    # print("    - Secure: System meets both security bounds with reasonable finality")
    # print("    - Insecure (System Bound Violation): Too many shards for given farmer count/malicious proportion")
    # print("    - Insecure (Fraud Detection Impossible): Cannot achieve fraud detection security with reshuffling")
    # print("    - Questionable (Long Finality Delay): Security achievable but with impractical finality times")
    # print()
    # print("  System Security Analysis:")
    # print("    - Uses Chernoff bound to ensure probability of any shard having ≥50% malicious farmers is extremely low")
    # print("    - Critical for preventing immediate shard takeover attacks")
    # print()
    # print("  Fraud Detection Security:")
    # print("    - Models periodic reshuffling with full-state downloads for fraud detection")
    # print("    - Ensures fraudulent blocks/segments are eventually detected by honest farmers")
    # print("    - Determines minimum reshuffles needed before probabilistic finality")
    # print()
    # print("  Finality Implications:")
    # print("    - True finality requires waiting for sufficient reshuffles to ensure fraud detection")
    # print("    - Finality delay = (Min Reshuffles) × (Reshuffle Interval)")
    # print("    - Balance between security and user experience")

if __name__ == "__main__":
    main()