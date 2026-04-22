"""
Base CPU Scheduling Algorithms
Implements FCFS, SJF, Round Robin, and Priority Scheduling
as baseline comparisons for the AEAS algorithm.
"""

from scheduler.utils import deep_copy_processes, compute_metrics


#  Context switch overhead constant (time units)

# No global CONTEXT_SWITCH_TIME; passed as argument

def run_fcfs(processes, context_switch_time=0.5):
    """
    First Come First Serve (FCFS) Scheduling.
    Non-preemptive. Processes execute in order of arrival time.
    
    Args:
        processes: List of dicts with keys: id, arrival_time, burst_time, priority
        
    Returns:
        Dictionary with 'processes', 'gantt', 'metrics', 'total_time'
    """
    procs = deep_copy_processes(processes)
    procs.sort(key=lambda p: (p['arrival_time'], p['id']))
    
    current_time = 0.0
    gantt = []
    completed = []
    
    for i, proc in enumerate(procs):
        # Handle idle time if process hasn't arrived yet
        if current_time < proc['arrival_time']:
            idle_duration = proc['arrival_time'] - current_time
            gantt.append({
                'process': 'IDLE',
                'start': round(current_time, 2),
                'end': round(proc['arrival_time'], 2),
                'duration': round(idle_duration, 2),
                'frequency': 'IDLE'
            })
            current_time = proc['arrival_time']
        
        # Context switch (except for first process)
        if i > 0 and context_switch_time > 0:
            gantt.append({
                'process': 'CTX_SWITCH',
                'start': round(current_time, 2),
                'end': round(current_time + context_switch_time, 2),
                'duration': context_switch_time,
                'frequency': 'LOW'
            })
            current_time += context_switch_time
        
        start_time = current_time
        end_time = current_time + proc['burst_time']
        
        gantt.append({
            'process': proc['id'],
            'start': round(start_time, 2),
            'end': round(end_time, 2),
            'duration': proc['burst_time'],
            'frequency': 'HIGH'  # Baseline always runs at HIGH
        })
        
        proc['start_time'] = round(start_time, 2)
        proc['completion_time'] = round(end_time, 2)
        proc['waiting_time'] = round(start_time - proc['arrival_time'], 2)
        proc['turnaround_time'] = round(end_time - proc['arrival_time'], 2)
        
        current_time = end_time
        completed.append(proc)
    
    total_time = round(current_time, 2)
    metrics = compute_metrics(completed, total_time)
    
    return {
        'algorithm': 'FCFS',
        'processes': completed,
        'gantt': gantt,
        'metrics': metrics,
        'total_time': total_time
    }

def run_sjf(processes, context_switch_time=0.5):
    """
    Shortest Job First (SJF) Scheduling.
    Non-preemptive. Selects the process with the shortest burst time from ready queue.
    
    Args:
        processes: List of dicts with keys: id, arrival_time, burst_time, priority
        
    Returns:
        Dictionary with 'processes', 'gantt', 'metrics', 'total_time'
    """
    procs = deep_copy_processes(processes)
    n = len(procs)
    current_time = 0.0
    completed = []
    completed_ids = set()
    gantt = []
    switch_count = 0
    
    while len(completed) < n:
        # Get ready queue
        ready = [p for p in procs if p['arrival_time'] <= current_time and p['id'] not in completed_ids]
        
        if not ready:
            # Find next arriving process
            future = [p for p in procs if p['id'] not in completed_ids]
            next_arrival = min(p['arrival_time'] for p in future)
            gantt.append({
                'process': 'IDLE',
                'start': round(current_time, 2),
                'end': round(next_arrival, 2),
                'duration': round(next_arrival - current_time, 2),
                'frequency': 'IDLE'
            })
            current_time = next_arrival
            continue
        
        # Select shortest burst time process
        ready.sort(key=lambda p: (p['burst_time'], p['arrival_time']))
        selected = ready[0]
        
        # Context switch
        if switch_count > 0 and context_switch_time > 0:
            gantt.append({
                'process': 'CTX_SWITCH',
                'start': round(current_time, 2),
                'end': round(current_time + context_switch_time, 2),
                'duration': context_switch_time,
                'frequency': 'LOW'
            })
            current_time += context_switch_time
        
        start_time = current_time
        end_time = current_time + selected['burst_time']
        
        gantt.append({
            'process': selected['id'],
            'start': round(start_time, 2),
            'end': round(end_time, 2),
            'duration': selected['burst_time'],
            'frequency': 'HIGH'
        })
        
        selected['start_time'] = round(start_time, 2)
        selected['completion_time'] = round(end_time, 2)
        selected['waiting_time'] = round(start_time - selected['arrival_time'], 2)
        selected['turnaround_time'] = round(end_time - selected['arrival_time'], 2)
        
        current_time = end_time
        completed_ids.add(selected['id'])
        completed.append(selected)
        switch_count += 1
    
    total_time = round(current_time, 2)
    metrics = compute_metrics(completed, total_time)
    
    return {
        'algorithm': 'SJF',
        'processes': completed,
        'gantt': gantt,
        'metrics': metrics,
        'total_time': total_time
    }

def run_round_robin(processes, quantum=3, context_switch_time=0.5):
    """
    Round Robin (RR) Scheduling.
    Preemptive with time quantum. Each process runs for at most 'quantum' time units.
    
    Args:
        processes: List of dicts with keys: id, arrival_time, burst_time, priority
        quantum: Time quantum for each cycle (default: 3)
        
    Returns:
        Dictionary with 'processes', 'gantt', 'metrics', 'total_time'
    """
    procs = deep_copy_processes(processes)
    n = len(procs)
    
    # Initialize remaining burst times
    for p in procs:
        p['remaining'] = p['burst_time']
    
    procs.sort(key=lambda p: (p['arrival_time'], p['id']))
    
    current_time = 0.0
    completed = []
    completed_ids = set()
    gantt = []
    queue = []
    last_process = None
    
    # Add first arrived processes
    for p in procs:
        if p['arrival_time'] <= current_time:
            queue.append(p)
    
    while len(completed) < n:
        if not queue:
            # Find next arriving process
            future = [p for p in procs if p['id'] not in completed_ids and p not in queue]
            if not future:
                break
            next_arrival = min(p['arrival_time'] for p in future)
            gantt.append({
                'process': 'IDLE',
                'start': round(current_time, 2),
                'end': round(next_arrival, 2),
                'duration': round(next_arrival - current_time, 2),
                'frequency': 'IDLE'
            })
            current_time = next_arrival
            for p in procs:
                if p['arrival_time'] <= current_time and p['id'] not in completed_ids and p not in queue:
                    queue.append(p)
            continue
        
        selected = queue.pop(0)
        
        # Context switch
        if last_process is not None and last_process != selected['id'] and context_switch_time > 0:
            gantt.append({
                'process': 'CTX_SWITCH',
                'start': round(current_time, 2),
                'end': round(current_time + context_switch_time, 2),
                'duration': context_switch_time,
                'frequency': 'LOW'
            })
            current_time += context_switch_time
        
        exec_time = min(quantum, selected['remaining'])
        start_time = current_time
        end_time = current_time + exec_time
        
        gantt.append({
            'process': selected['id'],
            'start': round(start_time, 2),
            'end': round(end_time, 2),
            'duration': round(exec_time, 2),
            'frequency': 'HIGH'
        })
        
        selected['remaining'] -= exec_time
        current_time = end_time
        last_process = selected['id']
        
        # Add newly arrived processes to queue before re-adding current
        for p in procs:
            if (p['arrival_time'] <= current_time and 
                p['id'] not in completed_ids and 
                p not in queue and p != selected):
                queue.append(p)
        
        if selected['remaining'] <= 0:
            selected['completion_time'] = round(end_time, 2)
            selected['turnaround_time'] = round(end_time - selected['arrival_time'], 2)
            selected['waiting_time'] = round(
                selected['turnaround_time'] - selected['burst_time'], 2
            )
            completed_ids.add(selected['id'])
            completed.append(selected)
        else:
            queue.append(selected)
    
    total_time = round(current_time, 2)
    metrics = compute_metrics(completed, total_time)
    
    return {
        'algorithm': 'Round Robin',
        'processes': completed,
        'gantt': gantt,
        'metrics': metrics,
        'total_time': total_time
    }

def run_priority(processes, context_switch_time=0.5):
    """
    Priority Scheduling (Non-preemptive).
    Lower priority number = higher priority. Selects highest priority from ready queue.
    
    Args:
        processes: List of dicts with keys: id, arrival_time, burst_time, priority
        
    Returns:
        Dictionary with 'processes', 'gantt', 'metrics', 'total_time'
    """
    procs = deep_copy_processes(processes)
    n = len(procs)
    current_time = 0.0
    completed = []
    completed_ids = set()
    gantt = []
    switch_count = 0
    
    while len(completed) < n:
        # Get ready queue
        ready = [p for p in procs if p['arrival_time'] <= current_time and p['id'] not in completed_ids]
        
        if not ready:
            future = [p for p in procs if p['id'] not in completed_ids]
            next_arrival = min(p['arrival_time'] for p in future)
            gantt.append({
                'process': 'IDLE',
                'start': round(current_time, 2),
                'end': round(next_arrival, 2),
                'duration': round(next_arrival - current_time, 2),
                'frequency': 'IDLE'
            })
            current_time = next_arrival
            continue
        
        # Select highest priority (lowest number)
        ready.sort(key=lambda p: (p['priority'], p['arrival_time']))
        selected = ready[0]
        
        # Context switch
        if switch_count > 0 and context_switch_time > 0:
            gantt.append({
                'process': 'CTX_SWITCH',
                'start': round(current_time, 2),
                'end': round(current_time + context_switch_time, 2),
                'duration': context_switch_time,
                'frequency': 'LOW'
            })
            current_time += context_switch_time
        
        start_time = current_time
        end_time = current_time + selected['burst_time']
        
        gantt.append({
            'process': selected['id'],
            'start': round(start_time, 2),
            'end': round(end_time, 2),
            'duration': selected['burst_time'],
            'frequency': 'HIGH'
        })
        
        selected['start_time'] = round(start_time, 2)
        selected['completion_time'] = round(end_time, 2)
        selected['waiting_time'] = round(start_time - selected['arrival_time'], 2)
        selected['turnaround_time'] = round(end_time - selected['arrival_time'], 2)
        
        current_time = end_time
        completed_ids.add(selected['id'])
        completed.append(selected)
        switch_count += 1
    
    total_time = round(current_time, 2)
    metrics = compute_metrics(completed, total_time)
    
    return {
        'algorithm': 'Priority',
        'processes': completed,
        'gantt': gantt,
        'metrics': metrics,
        'total_time': total_time
    }
