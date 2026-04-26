"""
Adaptive Energy-Aware Scheduler (AEAS)

A custom CPU scheduling algorithm that minimizes energy consumption
through intelligent process classification and DVFS integration,
while maintaining performance degradation ≤ 5%.

Algorithm Design:
    Each process Pi = (ATi, BTi, Pri)
    Maintain: Ready Queue RQ(t), Current time t, Gantt timeline G

Classification:
    CRITICAL → priority ≤ 2   → HIGH frequency (2.0W)
    SHORT    → BT ≤ median(BT) → MEDIUM frequency (0.8W)
    LONG     → others          → LOW frequency (0.3W)

DVFS Rules:
    |RQ| > 5  → non-critical forced to LOW
    |RQ| > 3  → non-critical reduced one level
    wait_time > threshold → boost frequency (starvation prevention)
"""

from scheduler.utils import (
    deep_copy_processes, compute_metrics, compute_median, get_ready_queue
)
from energy.dvfs import (
    assign_base_frequency, apply_dvfs_adjustment, get_power,
    URGENCY_WAIT_THRESHOLD
)
# Context switch power constraint
CONTEXT_SWITCH_POWER = 0.3  # Watts during context switch


def classify_process(process, threshold):
    """
    Classify a process into CRITICAL, SHORT, or LONG category.

    Rules:
        - CRITICAL: priority ≤ 2 (urgent system tasks)
        - SHORT:    burst_time ≤ adaptive threshold (quick tasks)
        - LONG:     everything else (background / heavy tasks)

    Args:
        process: Process dict with 'priority' and 'burst_time'
        threshold: Adaptive threshold (median burst time of ready queue)

    Returns:
        Classification string: 'CRITICAL', 'SHORT', or 'LONG'
    """
    if process['priority'] <= 2:
        return 'CRITICAL'
    elif process['burst_time'] <= threshold:
        return 'SHORT'
    else:
        return 'LONG'


def compute_adaptive_threshold(ready_queue):
    """
    Compute the adaptive threshold T as the median burst time of the ready queue.

    T = median(BT of all processes in RQ)

    This ensures the SHORT/LONG boundary adapts dynamically to the current
    workload composition rather than using a static cutoff.

    Args:
        ready_queue: List of processes currently in the ready queue

    Returns:
        Median burst time value
    """
    burst_times = [p['burst_time'] for p in ready_queue]
    return compute_median(burst_times)


def sort_ready_queue(ready_queue, threshold, current_time):
    """
    Sort the ready queue using the AEAS multi-key ordering:
        Primary:   Process class (CRITICAL=0, SHORT=1, LONG=2)
        Secondary: Burst time (ascending — favor shorter tasks within class)
        Tertiary:  Arrival time (ascending — FCFS tiebreaker)

    Urgent processes (starving too long) are promoted to the front.

    Args:
        ready_queue: List of processes in the ready queue
        threshold: Adaptive threshold for classification
        current_time: Current simulation time

    Returns:
        Sorted ready queue with classification annotations
    """
    class_order = {'CRITICAL': 0, 'SHORT': 1, 'LONG': 2}

    for p in ready_queue:
        p['class'] = classify_process(p, threshold)
        p['class_order'] = class_order[p['class']]
        p['current_wait'] = current_time - p['arrival_time']

    # Separate urgent processes (starvation prevention)
    urgent = [p for p in ready_queue if p['current_wait'] >= URGENCY_WAIT_THRESHOLD]
    normal = [p for p in ready_queue if p['current_wait'] < URGENCY_WAIT_THRESHOLD]

    # Sort urgent by wait time (longest wait first)
    urgent.sort(key=lambda p: -p['current_wait'])

    # Sort normal by (class, burst_time, arrival_time)
    normal.sort(key=lambda p: (p['class_order'], p['burst_time'], p['arrival_time']))

    # Urgent processes go first, then normal ordering
    return urgent + normal


def run_aeas(processes, dvfs_enabled=True, context_switch_time=0.5):
    """
    Execute the Adaptive Energy-Aware Scheduler (AEAS) algorithm.

    This is the core contribution of the project. The algorithm:
    1. Dynamically classifies processes using an adaptive median threshold
    2. Applies DVFS to assign appropriate frequency/voltage levels
    3. Groups same-class processes to minimize context switch overhead
    4. Includes starvation prevention for fairness guarantees

    Args:
        processes: List of process dicts with keys:
                   id, arrival_time, burst_time, priority
        dvfs_enabled: Whether to enable DVFS optimization (default: True)

    Returns:
        Dictionary with:
            - algorithm: 'AEAS'
            - processes: Completed processes with timing info
            - gantt: Gantt chart timeline entries
            - metrics: Performance metrics
            - total_time: Total simulation time
            - energy_details: Per-process frequency and class assignments
            - dvfs_enabled: Whether DVFS was active
    """
    procs = deep_copy_processes(processes)
    n = len(procs)

    current_time = 0.0
    completed = []
    completed_ids = set()
    gantt = []
    energy_details = []
    switch_count = 0

    while len(completed) < n:
        # ─── Step A: Add arrived processes to ready queue ───
        ready = [p for p in procs
                 if p['arrival_time'] <= current_time and p['id'] not in completed_ids]

        # ─── Step B: Handle empty ready queue (IDLE) ───
        if not ready:
            future = [p for p in procs if p['id'] not in completed_ids]
            if not future:
                break
            next_arrival = min(p['arrival_time'] for p in future)
            idle_duration = next_arrival - current_time

            gantt.append({
                'process': 'IDLE',
                'start': round(current_time, 2),
                'end': round(next_arrival, 2),
                'duration': round(idle_duration, 2),
                'frequency': 'IDLE'
            })
            current_time = next_arrival
            continue

        # ─── Step C: Compute adaptive threshold ───
        threshold = compute_adaptive_threshold(ready)

        # ─── Step D & E: Classify and sort ready queue ───
        sorted_queue = sort_ready_queue(ready, threshold, current_time)

        # ─── Step F: Select the highest-priority class group ───
        # Execute all processes in the top class group together
        # to minimize DVFS frequency transitions
        top_class = sorted_queue[0]['class']
        group = [p for p in sorted_queue if p['class'] == top_class]

        # ─── Step G: Execute each process in the group ───
        for proc in group:
            # Recalculate waiting time at actual execution moment
            waiting_time = current_time - proc['arrival_time']

            # Assign base frequency from classification
            base_freq = assign_base_frequency(proc['class'])

            # Apply DVFS adjustments based on load and starvation
            final_freq, is_urgent = apply_dvfs_adjustment(
                base_freq, proc['class'], len(ready), waiting_time, dvfs_enabled
            )

            # Context switch overhead (except for first process)
            if switch_count > 0 and context_switch_time > 0:
                gantt.append({
                    'process': 'CTX_SWITCH',
                    'start': round(current_time, 2),
                    'end': round(current_time + context_switch_time, 2),
                    'duration': context_switch_time,
                    'frequency': 'LOW'
                })
                current_time += context_switch_time

            # Execute the process
            start_time = current_time
            exec_duration = proc['burst_time']
            end_time = current_time + exec_duration

            gantt.append({
                'process': proc['id'],
                'start': round(start_time, 2),
                'end': round(end_time, 2),
                'duration': round(exec_duration, 2),
                'frequency': final_freq
            })

            # Record completion details
            proc['start_time'] = round(start_time, 2)
            proc['completion_time'] = round(end_time, 2)
            proc['waiting_time'] = round(start_time - proc['arrival_time'], 2)
            proc['turnaround_time'] = round(end_time - proc['arrival_time'], 2)
            proc['frequency'] = final_freq
            proc['is_urgent'] = is_urgent

            # Track energy details
            energy_details.append({
                'process_id': proc['id'],
                'class': proc['class'],
                'frequency': final_freq,
                'power': get_power(final_freq),
                'duration': round(exec_duration, 2),
                'energy': round(get_power(final_freq) * exec_duration, 4),
                'is_urgent': is_urgent
            })

            current_time = end_time
            completed_ids.add(proc['id'])
            completed.append(proc)
            switch_count += 1

    total_time = round(current_time, 2)
    metrics = compute_metrics(completed, total_time)

    return {
        'algorithm': 'AEAS',
        'processes': completed,
        'gantt': gantt,
        'metrics': metrics,
        'total_time': total_time,
        'energy_details': energy_details,
        'dvfs_enabled': dvfs_enabled
    }
