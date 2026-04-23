"""
Energy Model for the AEAS CPU Scheduler.
Provides power consumption calculations, energy accounting,
and the adaptive threshold computation using statistical median.
"""

from energy.dvfs import FREQUENCY_LEVELS, get_power, compute_energy

# ─────────────────────────────────────────────────────────────
#  Power Constants (Watts) — duplicated here for reference
# ─────────────────────────────────────────────────────────────
POWER_HIGH   = 2.0   # Critical tasks
POWER_MEDIUM = 0.8   # Short tasks
POWER_LOW    = 0.3   # Long / background tasks
POWER_IDLE   = 0.1   # CPU idle
POWER_CTX_SW = 0.3   # Context switch overhead



def compute_total_energy(gantt_chart):
    """
    Compute the total energy consumption from a Gantt chart.
    Each entry contains: process, start, end, duration, frequency.
    
    E_total = Σ P(f_i) × t_i
    
    Args:
        gantt_chart: List of Gantt chart entries
        
    Returns:
        Dictionary with energy breakdown
    """
    total_energy = 0.0
    idle_energy = 0.0
    context_switch_energy = 0.0
    process_energy = {}
    
    for entry in gantt_chart:
        freq = entry.get('frequency', 'HIGH')
        duration = entry.get('duration', 0)
        power = get_power(freq) if freq != 'IDLE' else POWER_IDLE
        
        if entry['process'] == 'CTX_SWITCH':
            power = POWER_CTX_SW
        
        energy = compute_energy(power, duration)
        total_energy += energy
        
        if entry['process'] == 'IDLE':
            idle_energy += energy
        elif entry['process'] == 'CTX_SWITCH':
            context_switch_energy += energy
        else:
            pid = entry['process']
            process_energy[pid] = process_energy.get(pid, 0) + energy
    
    return {
        'total_energy': round(total_energy, 4),
        'idle_energy': round(idle_energy, 4),
        'context_switch_energy': round(context_switch_energy, 4),
        'process_energy': {k: round(v, 4) for k, v in process_energy.items()},
        'active_energy': round(total_energy - idle_energy - context_switch_energy, 4)
    }


def compute_baseline_energy(gantt_chart):
    """
    Compute what the energy would be if all processes ran at HIGH frequency.
    Used for comparison to show AEAS energy savings.
    
    Args:
        gantt_chart: List of Gantt chart entries
        
    Returns:
        Total energy if everything ran at full power
    """
    total = 0.0
    for entry in gantt_chart:
        duration = entry.get('duration', 0)
        if entry['process'] == 'IDLE':
            total += POWER_IDLE * duration
        elif entry['process'] == 'CTX_SWITCH':
            total += POWER_CTX_SW * duration
        else:
            total += POWER_HIGH * duration  # Force HIGH for baseline
    return round(total, 4)


def compute_energy_savings(aeas_energy, baseline_energy):
    """
    Compute the percentage of energy saved by AEAS vs a baseline.
    
    Energy Saved % = ((baseline - aeas) / baseline) × 100
    
    Args:
        aeas_energy: Total energy consumed by AEAS
        baseline_energy: Total energy consumed by baseline algorithm
        
    Returns:
        Energy savings percentage
    """
    if baseline_energy <= 0:
        return 0.0
    return round(((baseline_energy - aeas_energy) / baseline_energy) * 100, 2)


def compute_performance_change(aeas_metrics, baseline_metrics):
    """
    Compute the percentage change in average waiting time (performance).
    Positive value = AEAS is worse (longer wait), negative = AEAS is better.
    
    Performance Change % = ((AEAS_WT - Baseline_WT) / Baseline_WT) × 100
    
    Args:
        aeas_metrics: AEAS performance metrics dict
        baseline_metrics: Baseline algorithm performance metrics dict
        
    Returns:
        Performance change percentage
    """
    baseline_wt = baseline_metrics.get('avg_waiting_time', 0)
    aeas_wt = aeas_metrics.get('avg_waiting_time', 0)
    
    if baseline_wt <= 0:
        return 0.0
    
    return round(((aeas_wt - baseline_wt) / baseline_wt) * 100, 2)


def compute_efficiency_score(throughput, total_energy):
    """
    Compute the efficiency score: throughput divided by total energy.
    Higher is better — more work done per unit of energy.
    
    Efficiency = Throughput / Total Energy
    
    Args:
        throughput: Processes completed per time unit
        total_energy: Total energy consumed (Joules)
        
    Returns:
        Efficiency score
    """
    if total_energy <= 0:
        return 0.0
    return round(throughput / total_energy, 6)
