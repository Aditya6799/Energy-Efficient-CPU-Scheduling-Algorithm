"""
Tests for the AEAS Scheduler and Baseline Algorithms.
Validates correctness of scheduling logic, ordering, and metrics.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scheduler.energy_scheduler import run_aeas, classify_process, compute_adaptive_threshold
from scheduler.base_algorithms import run_fcfs, run_sjf, run_round_robin, run_priority
from scheduler.utils import compute_median


# ─────────────────────────────────────────────────────────────
#  Test Fixtures
# ─────────────────────────────────────────────────────────────
@pytest.fixture
def basic_processes():
    """Standard 5-process test set."""
    return [
        {'id': 'P1', 'arrival_time': 0, 'burst_time': 6, 'priority': 1},
        {'id': 'P2', 'arrival_time': 1, 'burst_time': 3, 'priority': 4},
        {'id': 'P3', 'arrival_time': 2, 'burst_time': 8, 'priority': 3},
        {'id': 'P4', 'arrival_time': 3, 'burst_time': 2, 'priority': 2},
        {'id': 'P5', 'arrival_time': 4, 'burst_time': 5, 'priority': 5},
    ]


@pytest.fixture
def same_arrival_processes():
    """All processes arrive at time 0."""
    return [
        {'id': 'P1', 'arrival_time': 0, 'burst_time': 5, 'priority': 3},
        {'id': 'P2', 'arrival_time': 0, 'burst_time': 2, 'priority': 1},
        {'id': 'P3', 'arrival_time': 0, 'burst_time': 8, 'priority': 4},
        {'id': 'P4', 'arrival_time': 0, 'burst_time': 3, 'priority': 2},
        {'id': 'P5', 'arrival_time': 0, 'burst_time': 6, 'priority': 5},
    ]


@pytest.fixture
def single_process():
    """Edge case with a single process."""
    return [
        {'id': 'P1', 'arrival_time': 0, 'burst_time': 5, 'priority': 3}
    ]


# ─────────────────────────────────────────────────────────────
#  AEAS Algorithm Tests
# ─────────────────────────────────────────────────────────────
class TestAEAS:
    def test_aeas_completes_all_processes(self, basic_processes):
        """All processes must complete."""
        result = run_aeas(basic_processes)
        assert len(result['processes']) == 5
    
    def test_aeas_returns_required_keys(self, basic_processes):
        """Result must contain all expected keys."""
        result = run_aeas(basic_processes)
        required = ['algorithm', 'processes', 'gantt', 'metrics', 'total_time',
                     'energy_details', 'dvfs_enabled']
        for key in required:
            assert key in result, f"Missing key: {key}"
    
    def test_aeas_critical_processes_first(self, same_arrival_processes):
        """Critical processes (priority ≤ 2) should execute before others."""
        result = run_aeas(same_arrival_processes)
        completed_ids = [p['id'] for p in result['processes']]
        # P2 (pri=1) and P4 (pri=2) are CRITICAL, should be in first positions
        critical_positions = [completed_ids.index('P2'), completed_ids.index('P4')]
        non_critical_positions = [completed_ids.index('P1'), completed_ids.index('P3'),
                                  completed_ids.index('P5')]
        assert max(critical_positions) < min(non_critical_positions)
    
    def test_aeas_dvfs_disabled(self, basic_processes):
        """When DVFS is off, all processes should run at HIGH frequency."""
        result = run_aeas(basic_processes, dvfs_enabled=False)
        for entry in result['gantt']:
            if entry['process'] not in ('IDLE', 'CTX_SWITCH'):
                assert entry['frequency'] == 'HIGH'
    
    def test_aeas_dvfs_enabled_varies_frequency(self, basic_processes):
        """When DVFS is on, frequencies should vary by classification."""
        result = run_aeas(basic_processes, dvfs_enabled=True)
        freqs = set()
        for entry in result['gantt']:
            if entry['process'] not in ('IDLE', 'CTX_SWITCH'):
                freqs.add(entry['frequency'])
        # With mixed priorities and burst times, we expect multiple frequency levels
        assert len(freqs) >= 2
    
    def test_aeas_single_process(self, single_process):
        """Single process edge case."""
        result = run_aeas(single_process)
        assert len(result['processes']) == 1
        assert result['processes'][0]['completion_time'] == 5
    
    def test_aeas_positive_metrics(self, basic_processes):
        """All metrics must be non-negative."""
        result = run_aeas(basic_processes)
        assert result['metrics']['avg_waiting_time'] >= 0
        assert result['metrics']['avg_turnaround_time'] >= 0
        assert result['metrics']['throughput'] > 0
        assert result['metrics']['cpu_utilization'] > 0


# ─────────────────────────────────────────────────────────────
#  Classification Tests
# ─────────────────────────────────────────────────────────────
class TestClassification:
    def test_critical_classification(self):
        """Priority ≤ 2 should be CRITICAL."""
        proc = {'priority': 1, 'burst_time': 10}
        assert classify_process(proc, 5) == 'CRITICAL'
    
    def test_short_classification(self):
        """BT ≤ threshold and priority > 2 should be SHORT."""
        proc = {'priority': 4, 'burst_time': 3}
        assert classify_process(proc, 5) == 'SHORT'
    
    def test_long_classification(self):
        """BT > threshold and priority > 2 should be LONG."""
        proc = {'priority': 4, 'burst_time': 8}
        assert classify_process(proc, 5) == 'LONG'
    
    def test_adaptive_threshold_median(self):
        """Threshold must be the median of burst times."""
        queue = [
            {'burst_time': 2}, {'burst_time': 5}, {'burst_time': 8},
            {'burst_time': 3}, {'burst_time': 6}
        ]
        threshold = compute_adaptive_threshold(queue)
        assert threshold == 5  # Median of [2, 3, 5, 6, 8]


# ─────────────────────────────────────────────────────────────
#  Baseline Algorithm Tests
# ─────────────────────────────────────────────────────────────
class TestBaselines:
    def test_fcfs_order(self, basic_processes):
        """FCFS executes processes in arrival order."""
        result = run_fcfs(basic_processes)
        ids = [p['id'] for p in result['processes']]
        assert ids == ['P1', 'P2', 'P3', 'P4', 'P5']
    
    def test_sjf_selects_shortest(self, same_arrival_processes):
        """SJF should execute shortest burst first when all arrive at 0."""
        result = run_sjf(same_arrival_processes)
        first = result['processes'][0]
        assert first['id'] == 'P2'  # BT=2 is shortest
    
    def test_round_robin_preempts(self, same_arrival_processes):
        """RR should preempt processes at quantum boundary."""
        result = run_round_robin(same_arrival_processes, quantum=3)
        # Should have more gantt entries than processes (due to preemption)
        process_entries = [g for g in result['gantt']
                          if g['process'] not in ('IDLE', 'CTX_SWITCH')]
        assert len(process_entries) > len(same_arrival_processes)
    
    def test_priority_selects_highest(self, same_arrival_processes):
        """Priority scheduling should execute highest priority first."""
        result = run_priority(same_arrival_processes)
        first = result['processes'][0]
        assert first['id'] == 'P2'  # Priority=1 is highest
    
    def test_all_baselines_complete(self, basic_processes):
        """All baselines must complete all processes."""
        for algo in [run_fcfs, run_sjf, run_round_robin, run_priority]:
            result = algo(basic_processes)
            assert len(result['processes']) == 5


# ─────────────────────────────────────────────────────────────
#  Utility Tests
# ─────────────────────────────────────────────────────────────
class TestUtils:
    def test_median_odd(self):
        """Median of odd-length list."""
        assert compute_median([1, 3, 5, 7, 9]) == 5
    
    def test_median_even(self):
        """Median of even-length list."""
        assert compute_median([1, 3, 5, 7]) == 4.0
    
    def test_median_empty(self):
        """Median of empty list should return 0."""
        assert compute_median([]) == 0
    
    def test_median_single(self):
        """Median of single element."""
        assert compute_median([42]) == 42


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
