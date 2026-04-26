"""
DVFS (Dynamic Voltage and Frequency Scaling) Module.
Handles frequency level assignment and dynamic adjustment based on system load.
"""

# ─────────────────────────────────────────────────────────────
#  DVFS Frequency Levels and Power Mapping
# ─────────────────────────────────────────────────────────────
FREQUENCY_LEVELS = {
    'HIGH':   {'power': 2.0, 'speed_factor': 1.0,  'voltage': 1.2},
    'MEDIUM': {'power': 0.8, 'speed_factor': 1.0,  'voltage': 0.9},
    'LOW':    {'power': 0.3, 'speed_factor': 1.0,  'voltage': 0.6},
    'IDLE':   {'power': 0.1, 'speed_factor': 0.0,  'voltage': 0.4}
}

# Frequency level ordering for adjustments
FREQ_ORDER = ['LOW', 'MEDIUM', 'HIGH']

# ─────────────────────────────────────────────────────────────
#  Starvation / urgency threshold (time units of waiting)
# ─────────────────────────────────────────────────────────────
URGENCY_WAIT_THRESHOLD = 10.0

# Maximum acceptable performance degradation
MAX_PERFORMANCE_LOSS_PCT = 5.0


def assign_base_frequency(process_class):
    """
    Assign the initial DVFS frequency level based on process classification.

    Classification → Frequency mapping:
        CRITICAL → HIGH   (2.0W)
        SHORT    → MEDIUM (0.8W)
        LONG     → LOW    (0.3W)

    Args:
        process_class: One of 'CRITICAL', 'SHORT', 'LONG'

    Returns:
        Frequency level string ('HIGH', 'MEDIUM', or 'LOW')
    """
    mapping = {
        'CRITICAL': 'HIGH',
        'SHORT': 'MEDIUM',
        'LONG': 'LOW'
    }
    return mapping.get(process_class, 'MEDIUM')


def reduce_frequency(current_freq):
    """
    Reduce the frequency by one level.
    HIGH → MEDIUM → LOW

    Args:
        current_freq: Current frequency level string

    Returns:
        Reduced frequency level string
    """
    idx = FREQ_ORDER.index(current_freq) if current_freq in FREQ_ORDER else 2
    new_idx = max(0, idx - 1)
    return FREQ_ORDER[new_idx]


def boost_frequency(current_freq):
    """
    Boost the frequency by one level.
    LOW → MEDIUM → HIGH

    Args:
        current_freq: Current frequency level string

    Returns:
        Boosted frequency level string
    """
    idx = FREQ_ORDER.index(current_freq) if current_freq in FREQ_ORDER else 0
    new_idx = min(len(FREQ_ORDER) - 1, idx + 1)
    return FREQ_ORDER[new_idx]


def apply_dvfs_adjustment(base_freq, process_class, queue_length, waiting_time, dvfs_enabled=True):
    """
    Apply dynamic DVFS adjustments based on current system load and process state.

    Rules (applied in order):
        1. If queue length > 5  → force non-critical to LOW
        2. If queue length > 3  → reduce non-critical by one level
        3. If waiting time exceeds threshold → boost frequency (starvation prevention)

    Args:
        base_freq: Initial frequency assignment from classify step
        process_class: 'CRITICAL', 'SHORT', or 'LONG'
        queue_length: Current number of processes in the ready queue
        waiting_time: How long this process has been waiting
        dvfs_enabled: Whether DVFS optimization is active

    Returns:
        Tuple of (final_frequency, is_urgent)
    """
    if not dvfs_enabled:
        return 'HIGH', False  # No DVFS: everything runs at full power

    freq = base_freq
    is_urgent = False

    # Rule 1: Heavy load → slam non-critical to LOW
    if queue_length > 5 and process_class != 'CRITICAL':
        freq = 'LOW'
    # Rule 2: Moderate load → reduce non-critical by one level
    elif queue_length > 3 and process_class != 'CRITICAL':
        freq = reduce_frequency(freq)

    # Rule 3: Starvation prevention → boost if waiting too long
    if waiting_time >= URGENCY_WAIT_THRESHOLD:
        freq = boost_frequency(freq)
        is_urgent = True

    return freq, is_urgent


def get_power(frequency):
    """
    Get the power consumption (in Watts) for a given frequency level.

    Args:
        frequency: Frequency level string ('HIGH', 'MEDIUM', 'LOW', 'IDLE')

    Returns:
        Power in Watts
    """
    return FREQUENCY_LEVELS.get(frequency, FREQUENCY_LEVELS['MEDIUM'])['power']


def compute_energy(power, duration):
    """
    Compute energy consumption: E = P × t

    Args:
        power: Power in Watts
        duration: Time in units

    Returns:
        Energy in Joules (Watt-seconds)
    """
    return power * duration
