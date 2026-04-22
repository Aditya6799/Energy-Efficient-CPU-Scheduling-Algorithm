"""
Utility functions for CPU scheduling algorithms.
Provides helper operations for sorting, queue management, and statistics.
"""

import statistics


def sort_by_arrival(processes):
    """Sort processes by arrival time (stable sort)."""
    return sorted(processes, key=lambda p: p['arrival_time'])


def sort_by_burst(processes):
    """Sort processes by burst time (Shortest Job First ordering)."""
    return sorted(processes, key=lambda p: p['burst_time'])


def sort_by_priority(processes):
    """Sort processes by priority (lower number = higher priority)."""
    return sorted(processes, key=lambda p: p['priority'])


def compute_median(values):
    """
    Compute the statistical median of a list of numeric values.
    Returns 0 if the list is empty.
    """
    if not values:
        return 0
    return statistics.median(values)


def get_ready_queue(processes, current_time, completed_ids):
    """
    Get all processes that have arrived by current_time and are not yet completed.
    
    Args:
        processes: List of process dicts with 'arrival_time' key
        current_time: Current simulation time
        completed_ids: Set of completed process IDs
        
    Returns:
        List of processes in the ready queue
    """
    return [
        p for p in processes
        if p['arrival_time'] <= current_time and p['id'] not in completed_ids
    ]


def compute_waiting_time(processes_result):
    """
    Compute the average waiting time from simulation results.
    Waiting Time = Completion Time - Arrival Time - Burst Time
    """
    if not processes_result:
        return 0
    total = sum(
        p['completion_time'] - p['arrival_time'] - p['burst_time']
        for p in processes_result
    )
    return total / len(processes_result)


def compute_turnaround_time(processes_result):
    """
    Compute the average turnaround time from simulation results.
    Turnaround Time = Completion Time - Arrival Time
    """
    if not processes_result:
        return 0
    total = sum(
        p['completion_time'] - p['arrival_time']
        for p in processes_result
    )
    return total / len(processes_result)


def compute_throughput(processes_result, total_time):
    """
    Compute throughput = number of processes / total time.
    """
    if total_time <= 0:
        return 0
    return len(processes_result) / total_time


def compute_cpu_utilization(processes_result, total_time):
    """
    Compute CPU utilization = total burst time / total elapsed time.
    """
    if total_time <= 0:
        return 0
    total_burst = sum(p['burst_time'] for p in processes_result)
    return (total_burst / total_time) * 100


def compute_metrics(processes_result, total_time):
    """
    Compute all standard scheduling performance metrics.
    
    Returns:
        Dictionary with avg_waiting_time, avg_turnaround_time,
        throughput, and cpu_utilization.
    """
    return {
        'avg_waiting_time': round(compute_waiting_time(processes_result), 2),
        'avg_turnaround_time': round(compute_turnaround_time(processes_result), 2),
        'throughput': round(compute_throughput(processes_result, total_time), 4),
        'cpu_utilization': round(compute_cpu_utilization(processes_result, total_time), 2)
    }


def deep_copy_processes(processes):
    """Create a deep copy of the process list to avoid mutation."""
    return [dict(p) for p in processes]
