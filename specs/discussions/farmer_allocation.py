import math
from scipy.stats import binom
from prettytable import PrettyTable

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
        return 0.0 # Invalid input
    if k_alpha > K_M:
        return 0.0 # Attacker doesn't have enough plots in total to achieve k_alpha

    p_success = 1.0 / N # Probability of a single plot landing in the target shard
    probability = binom.sf(k_alpha - 1, K_M, p_success) # P(X >= k_alpha)
    return probability

def find_min_K_M_for_success_prob(k_alpha, N, target_prob=0.9):
    """
    Finds the minimum total plots (K_M) an attacker needs to generate
    to achieve at least k_alpha plots in a target shard with 'target_prob' certainty.
    Assumes random allocation.

    This function iteratively increases K_M until the binomial survival function
    P(X >= k_alpha) reaches or exceeds the target_prob.
    """
    if k_alpha <= 0 or N <= 0:
        return 0
    if target_prob <= 0: # If attacker only needs >0 success prob, expectation is a good starting point
        # Return a slightly higher value than the simple expectation to ensure a non-zero probability
        return max(1, int(k_alpha * N * (1.0/0.51)))

    p_success_per_plot = 1.0 / N

    # Start with an initial guess for K_M, somewhat higher than expected value (k_alpha * N)
    # The expected number of plots in one shard is K_M * (1/N).
    # To get k_alpha plots, K_M should be at least k_alpha * N. We use 1.5x for a buffer.
    current_K_M = int(k_alpha * N * 1.5)
    if current_K_M == 0: current_K_M = 1 # Ensure K_M is at least 1

    # Special handling for k_alpha = 1, as the probability calculation simplifies.
    # P(X >= 1) = 1 - P(X = 0) = 1 - (1 - p_success_per_plot)^current_K_M
    if k_alpha == 1:
        if p_success_per_plot == 1.0: # Only possible if N=1, then K_M = 1 is enough for k_alpha=1
            return k_alpha
        # Solve for current_K_M: 1 - (1 - p_success_per_plot)^current_K_M >= target_prob
        # (1 - p_success_per_plot)^current_K_M <= 1 - target_prob
        # current_K_M * log(1 - p_success_per_plot) <= log(1 - target_prob)
        # current_K_M >= log(1 - target_prob) / log(1 - p_success_per_plot)
        required_K_M_for_1_plot = math.ceil(math.log(1 - target_prob) / math.log(1 - p_success_per_plot))
        current_K_M = max(current_K_M, int(required_K_M_for_1_plot))
        
    max_attempts = 2000 # Limit iterations to prevent extremely long runtimes
    step = max(1, int(current_K_M * 0.1)) # Increase step size as K_M grows to speed up convergence
    
    # Continuously increase K_M until the calculated attack probability meets the target
    while calculate_attack_probability(current_K_M, N, k_alpha) < target_prob and max_attempts > 0:
        current_K_M += step
        max_attempts -= 1
        # Cap K_M to a very large but finite number to avoid potential overflow or infinite loops
        if current_K_M > 10**12: 
            return float('inf') # Indicate that a solution could not be found within reasonable bounds
    
    # If loop finished due to max_attempts and target_prob not met
    if max_attempts == 0 and calculate_attack_probability(current_K_M, N, k_alpha) < target_prob:
        return float('inf') # Could not reach target probability within limits

    return current_K_M


def evaluate_scenario(
    num_shards,
    max_plot_size_gib,
    total_network_storage_pib,
    plotting_throughput_tib_hr_per_attacker,
    attacker_storage_percentage, # Re-interpretation based on attacker_model
    cost_per_plot_usd,
    global_history_size_gib,
    attacker_model="storage-limited", # NEW PARAMETER: "storage-limited" or "throughput-limited"
    target_attack_success_probability=0.9, # NEW PARAMETER: For throughput-limited attacker
    control_percentage_for_shard=0.51, # 51% for longest chain
    target_reshuffle_interval_hours=1,
    avg_block_time_seconds=5,
    avg_block_size_mb=1
):
    """
    Evaluates a single scenario and returns key metrics for concise display.
    """
    # Convert PiB to GiB for consistent calculations
    total_network_storage_gib = total_network_storage_pib * 1024 * 1024
    attacker_plotting_throughput_gib_hr = plotting_throughput_tib_hr_per_attacker * 1024

    # Shard Capacity and k_alpha
    # Determine the total storage capacity of a single shard
    target_storage_per_shard_gib = total_network_storage_gib / num_shards
    # Calculate the number of plots that can fit into a single shard
    plots_per_shard_capacity = math.floor(target_storage_per_shard_gib / max_plot_size_gib)
    if plots_per_shard_capacity == 0: # Ensure at least one plot for calculations if capacity is tiny
        plots_per_shard_capacity = 1

    # k_alpha: The number of plots an attacker needs to control (e.g., 51%) of a shard
    k_alpha = math.ceil(control_percentage_for_shard * plots_per_shard_capacity)
    if k_alpha == 0: # Ensure k_alpha is at least 1 if control is desired
        k_alpha = 1

    # Determine Piece Selection Risk and associated economic cost multiplier.
    # This reflects the intuition that a smaller global history makes it easier for an
    # attacker to strategically generate plots that are likely to contain specific pieces
    # leading to desired shard assignments. This is modeled as a REDUCED cost for the attacker.
    # The multiplier is applied to the attacker's cost_per_plot_usd.
    
    # Define thresholds as fractions of total_network_storage_gib for relative comparison
    # These percentages are illustrative and should be tuned based on specific blockchain properties.
    pib_to_gib_factor = 1024 * 1024
    total_net_storage_gib_value = total_network_storage_pib * pib_to_gib_factor

    piece_selection_risk = "Low (Very Large History relative to Network)"
    piece_selection_cost_multiplier = 1.0 # Default multiplier (no cost reduction for large history)

    # Thresholds based on global_history_size_gib relative to total_net_storage_gib_value
    # Example: If history is less than 0.1% of total network storage, it's very high risk.
    if total_net_storage_gib_value > 0: # Avoid division by zero if total_network_storage_pib is 0
        if global_history_size_gib < (0.001 * total_net_storage_gib_value): # < 0.1%
            piece_selection_risk = "Very High (Extremely Small History, Potentially Gamable)"
            piece_selection_cost_multiplier = 0.2 # 80% discount for attacker
        elif global_history_size_gib < (0.01 * total_net_storage_gib_value): # < 1%
            piece_selection_risk = "High (Small History relative to Network)"
            piece_selection_cost_multiplier = 0.5 # 50% discount
        elif global_history_size_gib < (0.05 * total_net_storage_gib_value): # < 5%
            piece_selection_risk = "Medium (Moderate History relative to Network)"
            piece_selection_cost_multiplier = 0.7 # 30% discount
        elif global_history_size_gib < (0.1 * total_net_storage_gib_value): # < 10%
            piece_selection_risk = "Low-Medium (Large History relative to Network)"
            piece_selection_cost_multiplier = 0.9 # 10% discount
    

    # Attacker's Total Plots (K_M) - calculation depends on the attacker_model
    K_M_calculated = 0
    attacker_model_description = ""
    
    if attacker_model == "storage-limited":
        # In this model, K_M is limited by the attacker's available storage,
        # which is a percentage of the total network storage.
        attacker_total_storage_gib = total_network_storage_gib * attacker_storage_percentage
        K_M_calculated = math.floor(attacker_total_storage_gib / max_plot_size_gib)
        attacker_model_description = f"Storage-Limited ({attacker_storage_percentage:.1%})"
    elif attacker_model == "throughput-limited":
        # In this model, the attacker can generate as many plots as their throughput allows,
        # aiming to achieve k_alpha plots in a target shard with a specified probability.
        # K_M is thus the number of plots required to reach that probability.
        K_M_calculated = find_min_K_M_for_success_prob(k_alpha, num_shards, target_attack_success_probability)
        attacker_model_description = f"Throughput-Limited (Prob. {target_attack_success_probability:.1%})"
    else:
        raise ValueError("Invalid attacker_model specified. Use 'storage-limited' or 'throughput-limited'.")

    K_M = max(1, K_M_calculated) # Ensure K_M is at least 1 for any calculations

    # Probability of Plotting Attack
    # This is the probability that the attacker's K_M plots (however they were derived)
    # result in at least k_alpha plots landing in a specific shard.
    prob_plotting_attack = calculate_attack_probability(K_M, num_shards, k_alpha)

    # Time for Attacker to Plot K_M plots
    plots_per_hr_per_attacker = attacker_plotting_throughput_gib_hr / max_plot_size_gib
    time_to_plot_km_hours = K_M / plots_per_hr_per_attacker if plots_per_hr_per_attacker > 0 else float('inf')

    # Economic Cost of Attack
    # This cost is affected by the piece_selection_cost_multiplier, reflecting the
    # added difficulty/cost of targeting specific pieces if history is small.
    economic_cost_of_attack_usd = K_M * cost_per_plot_usd * piece_selection_cost_multiplier

    # Cost of Honest Dedication (for comparison)
    # This represents the cost of filling one shard honestly, without any attack premium.
    # We use the base cost_per_plot_usd, not the multiplied one.
    cost_of_honest_shard_usd = plots_per_shard_capacity * cost_per_plot_usd
    
    # This represents the cost of the attacker's total storage if used honestly, without any multiplier.
    # Relevant for 'storage-limited' attacker model for comparison.
    honest_cost_for_attacker_storage_usd = (total_network_storage_gib * attacker_storage_percentage) / max_plot_size_gib * cost_per_plot_usd


    # Cost of Reshuffling (Data to Sync)
    # Calculates the amount of historical data a new farmer would need to download
    # to sync with a reshuffled shard within the target reshuffle interval.
    blocks_per_shard_per_hour = (target_reshuffle_interval_hours * 3600) / avg_block_time_seconds
    data_to_sync_per_shard_per_hour_gb = (blocks_per_shard_per_hour * avg_block_size_mb) / 1024 # MB to GB

    # Qualitative Assessment: Plotting Attack Risk
    # Assesses if the attacker can generate enough plots within the reshuffle interval.
    plotting_attack_risk = "Low (Time to plot >> Reshuffle)"
    if time_to_plot_km_hours <= target_reshuffle_interval_hours:
        plotting_attack_risk = "High (Time to plot <= Reshuffle)"
    elif time_to_plot_km_hours <= target_reshuffle_interval_hours * 24: # Within 24 hours
        plotting_attack_risk = "Medium (Time to plot ~ Day)"

    # Qualitative Assessment: Allocation Probability Risk
    # Assesses the likelihood of an attacker gaining k_alpha plots in a shard purely by random chance.
    allocation_prob_risk = "Very Low"
    if prob_plotting_attack > 0.0001: # 0.01%
        allocation_prob_risk = "Moderate"
    if prob_plotting_attack > 0.01: # 1%
        allocation_prob_risk = "High"

    # Qualitative Assessment: Sync Feasibility
    # Assesses how demanding it is for a farmer to sync with a new shard after reshuffling.
    sync_feasibility = "Manageable"
    if data_to_sync_per_shard_per_hour_gb > 10: # >10 GB/hr is quite high for casual users
        sync_feasibility = "Demanding"
    elif data_to_sync_per_shard_per_hour_gb > 25:
        sync_feasibility = "Very Demanding"

    # Qualitative assessment for Economic Cost vs. Honest Dedication
    # Provides a qualitative comparison of the attack cost against a relevant honest cost baseline.
    economic_cost_vs_honest = "" 

    if attacker_model == "storage-limited":
        # For storage-limited attacker, compare attack cost (with multiplier) to the cost of their *total* storage if used honestly (without multiplier).
        if economic_cost_of_attack_usd < (honest_cost_for_attacker_storage_usd * 0.9):
            economic_cost_vs_honest = "Less than honest equivalent"
        elif economic_cost_of_attack_usd > (honest_cost_for_attacker_storage_usd * 1.1):
            economic_cost_vs_honest = "Higher than honest equivalent"
        else:
            economic_cost_vs_honest = "Comparable to honest equivalent"
    else: # Throughput-limited attacker
        # For throughput-limited attacker, compare attack cost (with multiplier) to the cost of filling *one shard* honestly (without multiplier).
        # This answers: "Is it cheaper to attack a shard than for that shard to exist honestly?"
        if economic_cost_of_attack_usd < (cost_of_honest_shard_usd * 0.9):
            economic_cost_vs_honest = "Less than 1 Shard Honest Cost"
        elif economic_cost_of_attack_usd > (cost_of_honest_shard_usd * 1.1):
            economic_cost_vs_honest = "Higher than 1 Shard Honest Cost"
        else:
            economic_cost_vs_honest = "Comparable to 1 Shard Honest Cost"

    # Qualitative Assessment: Shard Member Security
    # Based on the heuristic: "The number of members in a shard should be number of shards divided by 1100
    # to yield a high probability 10^-10 of a malicious majority."
    min_plots_per_shard_for_security = num_shards / 1100.0
    shard_member_security_risk = "Secure (Meets Min)"
    if plots_per_shard_capacity < min_plots_per_shard_for_security:
        shard_member_security_risk = "Vulnerable (Below Min)"
    elif plots_per_shard_capacity < min_plots_per_shard_for_security * 1.5: # Within 50% of the target
         shard_member_security_risk = "Borderline (Close to Min)"


    return {
        "Attacker Model": attacker_model_description,
        "N (Shards)": num_shards,
        "Net Storage (PiB)": total_network_storage_pib,
        "Plot Size (GiB)": max_plot_size_gib,
        # Display either attacker percentage or target probability based on the model
        "Attacker % / Target Prob.": f"{attacker_storage_percentage:.1%}" if attacker_model == "storage-limited" else f"{target_attack_success_probability:.1%}",
        "k_alpha (plots)": k_alpha,
        "K_M (plots)": f"{K_M:,.0f}", # Formatted for readability
        "Plotting Prob.": f"{prob_plotting_attack:.2e}", # Scientific notation for small probabilities
        "Plot Time (days)": f"{time_to_plot_km_hours / 24:.2f}",
        "Economic Cost (USD)": f"${economic_cost_of_attack_usd:,.0f}", # Formatted as currency
        "Base Plot Cost (USD)": f"${cost_per_plot_usd:.2f}", # Show original cost for clarity
        "Piece Sel. Multiplier": f"{piece_selection_cost_multiplier:.1f}x", # Show the applied multiplier
        "Cost vs. Honest": economic_cost_vs_honest,
        "Honest Shard Cost (USD)": f"${cost_of_honest_shard_usd:,.0f}", # New field for clarity
        "Global History (GiB)": f"{global_history_size_gib:,.0f}",
        "Reshuffle (hrs)": target_reshuffle_interval_hours,
        "Sync Data (GB/hr)": f"{data_to_sync_per_shard_per_hour_gb:.2f}",
        "Plots/Shard": plots_per_shard_capacity,
        "Min Plots/Shard": f"{min_plots_per_shard_for_security:.2f}",
        "Shard Member Security": shard_member_security_risk,
        "Plot Attack Risk": plotting_attack_risk,
        "Alloc. Prob. Risk": allocation_prob_risk,
        "Sync Feasibility": sync_feasibility,
        "Piece Sel. Risk": piece_selection_risk
    }

# --- Define Scenarios ---
# Define various scenarios to test the protocol parameters under different conditions.
# Each scenario includes parameters for network size, plot size, attacker capabilities,
# economic costs, and historical data size, along with specific attacker models.
scenarios = [
    {
        "name": "Nazar 10 Shards (Storage-Limited)",
        "num_shards": 10,
        "max_plot_size_gib": 64000,
        "total_network_storage_pib": 500,
        "plotting_throughput_tib_hr_per_attacker": 1000,
        "attacker_storage_percentage": 0.5,
        "cost_per_plot_usd": 0.25,
        "global_history_size_gib": 100000, # 100 TiB, falls into 'Medium (Moderate History)' -> 1.3x multiplier
        "attacker_model": "storage-limited",
        "target_reshuffle_interval_hours": 1
    },
    {
        "name": "Nazar 3 Shards (Throughput-Limited, 90% Prob)",
        "num_shards": 3,
        "max_plot_size_gib": 64000,
        "total_network_storage_pib": 500, # Total network storage still defines shard capacity
        "plotting_throughput_tib_hr_per_attacker": 1000,
        "attacker_storage_percentage": 0.5, # Placeholder, not directly used for K_M calculation in this mode
        "cost_per_plot_usd": 0.25,
        "global_history_size_gib": 100000, # 100 TiB, falls into 'Medium (Moderate History)' -> 1.3x multiplier
        "attacker_model": "throughput-limited",
        "target_attack_success_probability": 0.90, # Attacker aims for 90% probability of success
        "target_reshuffle_interval_hours": 1
    },
    # {
    #     "name": "S1: Large Net, Low Attacker (Storage)",
    #     "num_shards": 100,
    #     "max_plot_size_gib": 100,
    #     "total_network_storage_pib": 500,
    #     "plotting_throughput_tib_hr_per_attacker": 3.6,
    #     "attacker_storage_percentage": 0.01,
    #     "cost_per_plot_usd": 0.25,
    #     "global_history_size_gib": 1000000, # 1 PiB, falls into 'Low-Medium (Large History)' -> 1.1x multiplier
    #     "attacker_model": "storage-limited",
    #     "target_reshuffle_interval_hours": 1
    # },
    # {
    #     "name": "S2: Large Net, Med Attacker (Throughput, 99% Prob)",
    #     "num_shards": 100,
    #     "max_plot_size_gib": 100,
    #     "total_network_storage_pib": 500,
    #     "plotting_throughput_tib_hr_per_attacker": 3.6,
    #     "attacker_storage_percentage": 0.05, # Placeholder
    #     "cost_per_plot_usd": 0.25,
    #     "global_history_size_gib": 1000000, # 1 PiB, falls into 'Low-Medium (Large History)' -> 1.1x multiplier
    #     "attacker_model": "throughput-limited",
    #     "target_attack_success_probability": 0.99,
    #     "target_reshuffle_interval_hours": 1
    # },
    # {
    #     "name": "STEST3: Very Small History (Storage)", # Highlight Very High Piece Sel. Risk
    #     "num_shards": 10,
    #     "max_plot_size_gib": 100,
    #     "total_network_storage_pib": 10,
    #     "plotting_throughput_tib_hr_per_attacker": 3.6,
    #     "attacker_storage_percentage": 0.10,
    #     "cost_per_plot_usd": 0.25,
    #     "global_history_size_gib": 500, # 0.5 TiB -> 'Very High (Extremely Small History, Potentially Gamable)' -> 2.0x multiplier
    #     "attacker_model": "storage-limited",
    #     "target_reshuffle_interval_hours": 1
    # },
    # {
    #     "name": "STEST6: Small History (Throughput, 95% Prob)", # Highlight High Piece Sel. Risk
    #     "num_shards": 50,
    #     "max_plot_size_gib": 100,
    #     "total_network_storage_pib": 50,
    #     "plotting_throughput_tib_hr_per_attacker": 10,
    #     "attacker_storage_percentage": 0.05,
    #     "cost_per_plot_usd": 0.25,
    #     "global_history_size_gib": 5000, # 5 TiB -> 'High (Small History)' -> 1.5x multiplier
    #     "attacker_model": "throughput-limited",
    #     "target_attack_success_probability": 0.95,
    #     "target_reshuffle_interval_hours": 1
    # },
    # {
    #     "name": "STEST7: Large History (Throughput, 90% Prob)", # Low Piece Sel. Risk (baseline)
    #     "num_shards": 200,
    #     "max_plot_size_gib": 100,
    #     "total_network_storage_pib": 1000, # 1 PiB
    #     "plotting_throughput_tib_hr_per_attacker": 100,
    #     "attacker_storage_percentage": 0.01,
    #     "cost_per_plot_usd": 0.25,
    #     "global_history_size_gib": 2000000, # 2 PiB -> 'Low (Very Large History)' -> 1.0x multiplier
    #     "attacker_model": "throughput-limited",
    #     "target_attack_success_probability": 0.90,
    #     "target_reshuffle_interval_hours": 1
    # },
    # {
    #     "name": "STEST4: Shard Security Test - Vulnerable (Storage)",
    #     "num_shards": 100,
    #     "max_plot_size_gib": 1024, # Larger plot size to reduce plots_per_shard_capacity
    #     "total_network_storage_pib": 10, # Smaller network storage
    #     "plotting_throughput_tib_hr_per_attacker": 3.6,
    #     "attacker_storage_percentage": 0.05,
    #     "cost_per_plot_usd": 0.25,
    #     "global_history_size_gib": 1000000,
    #     "attacker_model": "storage-limited",
    #     "target_reshuffle_interval_hours": 1
    # },
    # {
    #     "name": "STEST5: Shard Security Test - Secure (Throughput, 95% Prob)",
    #     "num_shards": 100,
    #     "max_plot_size_gib": 100, # Smaller plot size to increase plots_per_shard_capacity
    #     "total_network_storage_pib": 500, # Larger network storage
    #     "plotting_throughput_tib_hr_per_attacker": 3.6,
    #     "attacker_storage_percentage": 0.05, # Placeholder
    #     "cost_per_plot_usd": 0.25,
    #     "global_history_size_gib": 1000000,
    #     "attacker_model": "throughput-limited",
    #     "target_attack_success_probability": 0.95,
    #     "target_reshuffle_interval_hours": 1
    # },
]

# --- Execute and Display ---
def main():
    # Define the parameters that will be displayed as rows
    # This list explicitly names all the fields that `evaluate_scenario` returns
    # and will form the left-most column of the pivoted table.
    parameter_fields = [
        "Attacker Model", "N (Shards)", "Net Storage (PiB)", "Plot Size (GiB)",
        "Attacker % / Target Prob.", "k_alpha (plots)", "K_M (plots)", "Plotting Prob.", "Plot Time (days)",
        "Economic Cost (USD)", "Honest Shard Cost (USD)", "Economic Cost of Attack (USD)", "Base Plot Cost (USD)", "Piece Sel. Multiplier", "Cost vs. Honest",
        "Global History (GiB)", "Reshuffle (hrs)", "Sync Data (GB/hr)",
        "Plots/Shard", "Min Plots/Shard", "Shard Member Security",
        "Plot Attack Risk", "Alloc. Prob. Risk",
        "Sync Feasibility", "Piece Sel. Risk"
    ]

    # Collect results from all scenarios
    scenario_results = []
    scenario_names = []

    for scenario_params in scenarios:
        scenario_name = scenario_params.pop("name")
        scenario_names.append(scenario_name) # Store scenario names for column headers

        # Set default attacker_model if not specified in scenario_params
        if "attacker_model" not in scenario_params:
            scenario_params["attacker_model"] = "storage-limited"
        
        row_data = evaluate_scenario(**scenario_params)
        scenario_results.append(row_data) # Store the dictionary of results for this scenario

    # Create the pivoted table
    table = PrettyTable()
    
    # The first column header is "Parameter"
    # Subsequent column headers are the names of the scenarios
    table.field_names = ["Parameter"] + scenario_names
    table.align = "l" # Align the parameter column to the left
    
    # Align scenario columns to the right for numerical data, or center for qualitative
    # We'll set a default alignment for all scenario columns
    for _ in scenario_names:
        table.align[_] = "c" # Center align scenario columns for general display

    # Populate the table row by row, where each row corresponds to a parameter
    for field in parameter_fields:
        row_values = [field] # Start the row with the parameter name
        for result_dict in scenario_results:
            # Handle cases where a field might be missing (e.g., if a new field is added
            # and old scenario results don't have it, though with this structure it should be fine)
            row_values.append(result_dict.get(field, "N/A")) 
        table.add_row(row_values)

    # Print summary and the table
    print("--- Protocol Parameter Evaluation Summary (Pivoted View) ---")
    print("Metrics are calculated for achieving 51% control of a single shard.")
    print("Attacker Model: Specifies if the attacker is limited by storage (a percentage of network) or plotting throughput.")
    print("Attacker % / Target Prob.: For storage-limited, it's attacker's storage percentage. For throughput-limited, it's the target probability of achieving k_alpha plots in a shard.")
    print("K_M (plots): Total plots an attacker *has* (storage-limited) or *generates* (throughput-limited to achieve target prob).")
    print("Plotting Prob.: Probability of an attacker getting k_alpha plots in a specific shard (assuming random allocation).")
    print("Plot Time (days): Days for attacker to generate all their K_M plots.")
    print("Economic Cost (USD): Estimated total cost for an attacker to acquire K_M plots, adjusted by Piece Selection Multiplier.")
    print("Base Plot Cost (USD): The per-plot cost before any multipliers for piece selection difficulty.")
    print("Piece Sel. Multiplier: A factor increasing attacker's plotting cost if global history size makes piece selection more predictable/gamable.")
    print("Cost vs. Honest: Compares the economic cost of attack:")
    print("  - For storage-limited: Against the cost of honestly dedicating equivalent storage.")
    print("  - For throughput-limited: Against the cost of one shard's honest storage capacity.")
    print("Honest Shard Cost (USD): The total cost of plots needed to fill one shard honestly.")
    print("Global History (GiB): The assumed total size of the blockchain's historical data. Impacts piece selection predictability.")
    print("Sync Data (GB/hr): Data a farmer needs to download to sync 1 hour of blocks from new shard.")
    print("Plots/Shard: The calculated number of plots (members) per shard given network parameters.")
    print("Min Plots/Shard: The minimum recommended number of plots per shard to achieve a 10^-10 probability of malicious majority (based on num_shards / 1100).")
    print("\n" + str(table)) # Print the formatted table

    # Print the risk assessment legend for easy interpretation of results
    print("\n**Risk Assessment Legend:**")
    print("  Plot Attack Risk:")
    print("    - Low: Attacker cannot plot fast enough to respond to reshuffles (time to plot K_M is much greater than reshuffle interval).")
    print("    - Medium: Attacker could potentially plot enough within ~1 day (time to plot K_M is within 24 hours of reshuffle interval).")
    print("    - High: Attacker can plot enough within the reshuffle interval or less (time to plot K_M is less than or equal to reshuffle interval).")
    print("  Alloc. Prob. Risk:")
    print("    - Very Low: Probability of random allocation resulting in shard control is negligible (e.g., <= 0.0001%).")
    print("    - Moderate: Low but non-negligible probability (e.g., >0.0001% and <= 1%).")
    print("    - High: Significant probability (e.g., >1%).")
    print("  Sync Feasibility:")
    print("    - Manageable: Data sync is low, generally fine for most users (e.g., <= 10 GB/hr).")
    print("    - Demanding: Data sync is higher, may strain some connections or require optimized clients (e.g., >10 GB/hr and <= 25 GB/hr).")
    print("    - Very Demanding: High data sync, likely problematic for many users (e.g., >25 GB/hr).")
    print("  Cost vs. Honest:")
    print("    - Less than honest equivalent: The attack costs less than simply contributing the same storage honestly (storage-limited attacker).")
    print("    - Comparable to honest equivalent: The attack cost is roughly similar to honest contribution (storage-limited attacker).")
    print("    - Higher than honest equivalent: The attack is more expensive than honest contribution (storage-limited attacker).")
    print("    - Less than 1 Shard Honest Cost: The attack is cheaper than the honest cost of filling one shard (throughput-limited attacker).")
    print("    - Comparable to 1 Shard Honest Cost: The attack cost is roughly similar to one shard's honest cost (throughput-limited attacker).")
    print("    - Higher than 1 Shard Honest Cost: The attack is more expensive than one shard's honest cost (throughput-limited attacker).")
    print("  Piece Sel. Risk (History Size Impact):")
    print("    - Low (Very Large History): History size is massive (>1 PiB), making piece selection effectively random and practically unpredictable for an attacker. Multiplier: 1.0x")
    print("    - Low-Medium (Large History): History size is large (100 TiB - 1 PiB), piece selection remains very hard to manipulate. Multiplier: 1.1x")
    print("    - Medium (Moderate History): History size (10 TiB - 100 TiB) allows for some theoretical predictability, but still computationally demanding for an attacker. Multiplier: 1.3x")
    print("    - High (Small History): History size (1 TiB - 10 TiB) where the effective output space of piece indices is smaller, potentially increasing the feasibility of targeted plot generation for a very powerful attacker. Multiplier: 1.5x")
    print("    - Very High (Extremely Small History, Potentially Gamable): History size (<1 TiB) means the piece index space is very limited, making it significantly easier for an attacker to find public_keys that generate plots with desired piece distributions. This could be exploited with advanced computational resources using methods akin to birthday attacks on the reduced hash output space. Multiplier: 2.0x")
    print("  Shard Member Security:")
    print("    - Secure (Meets Min): The number of plots per shard meets or exceeds the minimum required to achieve a very low probability (10^-10) of a malicious majority via random allocation.")
    print("    - Borderline (Close to Min): The number of plots per shard is close to, but slightly below, the recommended minimum. May warrant closer inspection.")
    print("    - Vulnerable (Below Min): The number of plots per shard is significantly below the recommended minimum, indicating a higher probability of a malicious majority in a shard through random allocation.")

# Ensures main() is called only when the script is executed directly
if __name__ == "__main__":
    main()