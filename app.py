"""
Flask Application Server for AEAS Energy-Efficient CPU Scheduler.
Provides REST API endpoints for simulation, comparison, and evaluation.

API Routes:
    POST /api/simulate  → Run AEAS simulation
    POST /api/compare   → AEAS vs all baseline algorithms
    POST /api/evaluate  → Full evaluation with best algorithm recommendation
"""

import os
import sys
import json
from flask import Flask, request, jsonify, send_from_directory

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scheduler.energy_scheduler import run_aeas
from scheduler.base_algorithms import run_fcfs, run_sjf, run_round_robin, run_priority
from energy.energy_model import (
    compute_total_energy, compute_baseline_energy,
    compute_energy_savings, compute_performance_change,
    compute_efficiency_score
)
from energy.dvfs import MAX_PERFORMANCE_LOSS_PCT

# ─────────────────────────────────────────────────────────────
#  Flask App Configuration
# ─────────────────────────────────────────────────────────────
app = Flask(
    __name__,
    template_folder='frontend',
    static_folder='frontend',
    static_url_path='/static'
)


# ─────────────────────────────────────────────────────────────
#  Frontend Routes
# ─────────────────────────────────────────────────────────────
@app.route('/')
def index():
    """Serve the main dashboard HTML page."""
    return send_from_directory('frontend', 'index.html')


@app.route('/css/<path:filename>')
def serve_css(filename):
    """Serve CSS files from the frontend directory."""
    return send_from_directory('frontend', filename)


@app.route('/js/<path:filename>')
def serve_js(filename):
    """Serve JavaScript files from the frontend directory."""
    return send_from_directory('frontend', filename)


# ─────────────────────────────────────────────────────────────
#  Helper Functions
# ─────────────────────────────────────────────────────────────
def parse_processes(data):
    """
    Parse and validate process input from API request.

    Expected format per process:
        { id: str, arrival_time: float, burst_time: float, priority: int }
    """
    processes = data.get('processes', [])
    if not processes:
        return None, "No processes provided"

    parsed = []
    for i, p in enumerate(processes):
        try:
            parsed.append({
                'id': p.get('id', f'P{i+1}'),
                'arrival_time': float(p.get('arrival_time', 0)),
                'burst_time': float(p.get('burst_time', 1)),
                'priority': int(p.get('priority', 5))
            })
        except (ValueError, TypeError) as e:
            return None, f"Invalid process data at index {i}: {str(e)}"

    return parsed, None


def build_algorithm_result(result):
    """Build a standardized result with energy calculations."""
    energy = compute_total_energy(result['gantt'])
    baseline_energy = compute_baseline_energy(result['gantt'])

    return {
        'algorithm': result['algorithm'],
        'processes': result['processes'],
        'gantt': result['gantt'],
        'metrics': result['metrics'],
        'total_time': result['total_time'],
        'energy': energy,
        'baseline_energy_equivalent': baseline_energy,
        'energy_savings_vs_full_power': compute_energy_savings(
            energy['total_energy'], baseline_energy
        )
    }


# ─────────────────────────────────────────────────────────────
#  API Routes
# ─────────────────────────────────────────────────────────────
@app.route('/api/simulate', methods=['POST'])
def simulate():
    """
    POST /api/simulate

    Run the AEAS algorithm on provided processes.

    Request Body:
        {
            "processes": [...],
            "dvfs_enabled": true/false  (optional, default: true)
        }

    Returns:
        AEAS simulation results with energy breakdown and Gantt chart.
    """
    data = request.get_json()
    processes, error = parse_processes(data)
    if error:
        return jsonify({'error': error}), 400

    dvfs_enabled = data.get('dvfs_enabled', True)
    context_switch_time = float(data.get('context_switch_time', 0.5))

    # Run AEAS
    result = run_aeas(processes, dvfs_enabled=dvfs_enabled, context_switch_time=context_switch_time)
    response = build_algorithm_result(result)

    # Include AEAS-specific details
    response['energy_details'] = result.get('energy_details', [])
    response['dvfs_enabled'] = dvfs_enabled

    return jsonify(response)


@app.route('/api/compare', methods=['POST'])
def compare():
    """
    POST /api/compare

    Run AEAS against all baseline algorithms for comparison.

    Request Body:
        {
            "processes": [...],
            "dvfs_enabled": true/false  (optional, default: true)
        }

    Returns:
        Results for AEAS, FCFS, SJF, Round Robin, and Priority scheduling.
    """
    data = request.get_json()
    processes, error = parse_processes(data)
    if error:
        return jsonify({'error': error}), 400

    dvfs_enabled = data.get('dvfs_enabled', True)
    context_switch_time = float(data.get('context_switch_time', 0.5))

    # Run all algorithms
    aeas_result = run_aeas(processes, dvfs_enabled=dvfs_enabled, context_switch_time=context_switch_time)
    fcfs_result = run_fcfs(processes, context_switch_time=context_switch_time)
    sjf_result = run_sjf(processes, context_switch_time=context_switch_time)
    rr_result = run_round_robin(processes, context_switch_time=context_switch_time)
    priority_result = run_priority(processes, context_switch_time=context_switch_time)

    # Build response for each
    algorithms = {
        'AEAS': build_algorithm_result(aeas_result),
        'FCFS': build_algorithm_result(fcfs_result),
        'SJF': build_algorithm_result(sjf_result),
        'Round Robin': build_algorithm_result(rr_result),
        'Priority': build_algorithm_result(priority_result)
    }

    # Add AEAS specific details
    algorithms['AEAS']['energy_details'] = aeas_result.get('energy_details', [])
    algorithms['AEAS']['dvfs_enabled'] = dvfs_enabled

    # Compute comparative metrics
    comparisons = {}
    aeas_energy = algorithms['AEAS']['energy']['total_energy']
    aeas_metrics = algorithms['AEAS']['metrics']

    for name, algo in algorithms.items():
        if name == 'AEAS':
            continue

        algo_energy = algo['energy']['total_energy']
        energy_saved = compute_energy_savings(aeas_energy, algo_energy)
        perf_change = compute_performance_change(aeas_metrics, algo['metrics'])

        comparisons[name] = {
            'energy_saved_pct': energy_saved,
            'performance_change_pct': perf_change,
            'aeas_energy': aeas_energy,
            'baseline_energy': algo_energy
        }

    return jsonify({
        'algorithms': algorithms,
        'comparisons': comparisons,
        'dvfs_enabled': dvfs_enabled
    })


@app.route('/api/evaluate', methods=['POST'])
def evaluate():
    """
    POST /api/evaluate

    Full evaluation: runs all algorithms, computes energy/performance metrics,
    checks the ≤5% performance degradation constraint, and recommends
    the best algorithm.

    Request Body:
        {
            "processes": [...],
            "dvfs_enabled": true/false  (optional, default: true)
        }

    Returns:
        Comprehensive evaluation report with recommendation.
    """
    data = request.get_json()
    processes, error = parse_processes(data)
    if error:
        return jsonify({'error': error}), 400

    dvfs_enabled = data.get('dvfs_enabled', True)
    context_switch_time = float(data.get('context_switch_time', 0.5))

    # Run all algorithms
    results = {
        'AEAS': run_aeas(processes, dvfs_enabled=dvfs_enabled, context_switch_time=context_switch_time),
        'FCFS': run_fcfs(processes, context_switch_time=context_switch_time),
        'SJF': run_sjf(processes, context_switch_time=context_switch_time),
        'Round Robin': run_round_robin(processes, context_switch_time=context_switch_time),
        'Priority': run_priority(processes, context_switch_time=context_switch_time)
    }

    # Build evaluation data
    evaluation = {}
    for name, result in results.items():
        energy = compute_total_energy(result['gantt'])
        metrics = result['metrics']
        efficiency = compute_efficiency_score(
            metrics['throughput'], energy['total_energy']
        )

        evaluation[name] = {
            'metrics': metrics,
            'energy': energy,
            'efficiency_score': efficiency,
            'total_time': result['total_time']
        }

    # Compute AEAS vs each baseline
    aeas_eval = evaluation['AEAS']
    constraint_checks = {}
    baselines = ['FCFS', 'SJF', 'Round Robin', 'Priority']

    for baseline_name in baselines:
        baseline_eval = evaluation[baseline_name]

        energy_saved = compute_energy_savings(
            aeas_eval['energy']['total_energy'],
            baseline_eval['energy']['total_energy']
        )

        perf_change = compute_performance_change(
            aeas_eval['metrics'], baseline_eval['metrics']
        )

        # Check ≤5% performance degradation constraint
        constraint_pass = perf_change <= MAX_PERFORMANCE_LOSS_PCT

        constraint_checks[baseline_name] = {
            'energy_saved_pct': energy_saved,
            'performance_change_pct': perf_change,
            'constraint_pass': constraint_pass,
            'max_allowed_degradation': MAX_PERFORMANCE_LOSS_PCT
        }

    # Find best algorithm by efficiency score
    best_algo = max(evaluation.items(), key=lambda x: x[1]['efficiency_score'])

    # Overall constraint pass: AEAS must not degrade > 5% vs ANY baseline
    all_constraints_pass = all(
        c['constraint_pass'] for c in constraint_checks.values()
    )

    # Average energy savings across all baselines
    avg_energy_saved = sum(
        c['energy_saved_pct'] for c in constraint_checks.values()
    ) / len(constraint_checks) if constraint_checks else 0

    # Build recommendation
    if all_constraints_pass and avg_energy_saved > 0:
        recommendation = (
            f"AEAS reduces energy consumption by an average of {avg_energy_saved:.1f}% "
            f"compared to baseline algorithms while maintaining performance degradation "
            f"within the {MAX_PERFORMANCE_LOSS_PCT}% threshold. "
            f"It is suitable for mobile and embedded systems where power efficiency is critical."
        )
        recommendation_status = "OPTIMAL"
    elif avg_energy_saved > 0:
        recommendation = (
            f"AEAS achieves {avg_energy_saved:.1f}% average energy savings. "
            f"Some baselines show performance degradation slightly above the "
            f"{MAX_PERFORMANCE_LOSS_PCT}% target. Consider adjusting DVFS parameters."
        )
        recommendation_status = "ACCEPTABLE"
    else:
        recommendation = (
            "Under current workload conditions, AEAS energy savings are minimal. "
            "This is expected for very short or uniform workloads. "
            "AEAS excels with diverse, mixed-priority workloads."
        )
        recommendation_status = "NEUTRAL"

    return jsonify({
        'evaluation': evaluation,
        'constraint_checks': constraint_checks,
        'all_constraints_pass': all_constraints_pass,
        'avg_energy_saved_pct': round(avg_energy_saved, 2),
        'best_algorithm': {
            'name': best_algo[0],
            'efficiency_score': best_algo[1]['efficiency_score']
        },
        'recommendation': recommendation,
        'recommendation_status': recommendation_status,
        'dvfs_enabled': dvfs_enabled
    })


# ─────────────────────────────────────────────────────────────
#  Main Entry Point
# ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("============================================================")
    print("   AEAS - Adaptive Energy-Aware CPU Scheduler              ")
    print("   Energy-Efficient Scheduling for Mobile & Embedded       ")
    print("   Dashboard: http://127.0.0.1:5000                        ")
    print("============================================================")
    app.run(debug=True, port=5000)
