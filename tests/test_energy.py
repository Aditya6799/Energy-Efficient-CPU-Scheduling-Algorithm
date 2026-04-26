"""
Tests for the Energy Model and DVFS subsystem.
Validates power calculations, DVFS adjustments, and energy accounting.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from energy.energy_model import (
    compute_total_energy, compute_baseline_energy,
    compute_energy_savings, compute_performance_change,
    compute_efficiency_score
)
from energy.dvfs import (
    assign_base_frequency, apply_dvfs_adjustment,
    reduce_frequency, boost_frequency, get_power, compute_energy
)


# ─────────────────────────────────────────────────────────────
#  DVFS Assignment Tests
# ─────────────────────────────────────────────────────────────
class TestDVFS:
    def test_critical_gets_high(self):
        assert assign_base_frequency('CRITICAL') == 'HIGH'

    def test_short_gets_medium(self):
        assert assign_base_frequency('SHORT') == 'MEDIUM'

    def test_long_gets_low(self):
        assert assign_base_frequency('LONG') == 'LOW'

    def test_reduce_high_to_medium(self):
        assert reduce_frequency('HIGH') == 'MEDIUM'

    def test_reduce_medium_to_low(self):
        assert reduce_frequency('MEDIUM') == 'LOW'

    def test_reduce_low_stays_low(self):
        assert reduce_frequency('LOW') == 'LOW'

    def test_boost_low_to_medium(self):
        assert boost_frequency('LOW') == 'MEDIUM'

    def test_boost_medium_to_high(self):
        assert boost_frequency('MEDIUM') == 'HIGH'

    def test_boost_high_stays_high(self):
        assert boost_frequency('HIGH') == 'HIGH'

    def test_dvfs_disabled_returns_high(self):
        freq, urgent = apply_dvfs_adjustment('LOW', 'LONG', 3, 0, dvfs_enabled=False)
        assert freq == 'HIGH'

    def test_heavy_load_forces_low(self):
        """Queue > 5 should force non-critical to LOW."""
        freq, _ = apply_dvfs_adjustment('MEDIUM', 'SHORT', 6, 0, dvfs_enabled=True)
        assert freq == 'LOW'

    def test_moderate_load_reduces(self):
        """Queue > 3 should reduce non-critical by one level."""
        freq, _ = apply_dvfs_adjustment('HIGH', 'SHORT', 4, 0, dvfs_enabled=True)
        assert freq == 'MEDIUM'  # HIGH reduced to MEDIUM

    def test_critical_not_reduced(self):
        """Critical processes should not be reduced under load."""
        freq, _ = apply_dvfs_adjustment('HIGH', 'CRITICAL', 6, 0, dvfs_enabled=True)
        assert freq == 'HIGH'

    def test_starvation_boosts(self):
        """Long waiting time should boost frequency."""
        freq, urgent = apply_dvfs_adjustment('LOW', 'LONG', 2, 15, dvfs_enabled=True)
        assert freq == 'MEDIUM'  # LOW boosted to MEDIUM
        assert urgent is True


# ─────────────────────────────────────────────────────────────
#  Power & Energy Tests
# ─────────────────────────────────────────────────────────────
class TestPowerModel:
    def test_power_values(self):
        """Verify power constants match specification."""
        assert get_power('HIGH') == 2.0
        assert get_power('MEDIUM') == 0.8
        assert get_power('LOW') == 0.3

    def test_energy_formula(self):
        """E = P × t"""
        assert compute_energy(2.0, 5) == 10.0
        assert compute_energy(0.8, 3) == pytest.approx(2.4)
        assert compute_energy(0.3, 10) == pytest.approx(3.0)

    def test_total_energy_computation(self):
        """Test energy breakdown from a simple gantt chart."""
        gantt = [
            {'process': 'P1', 'start': 0, 'end': 5, 'duration': 5, 'frequency': 'HIGH'},
            {'process': 'CTX_SWITCH', 'start': 5, 'end': 5.5, 'duration': 0.5, 'frequency': 'LOW'},
            {'process': 'P2', 'start': 5.5, 'end': 8.5, 'duration': 3, 'frequency': 'MEDIUM'},
        ]
        result = compute_total_energy(gantt)

        # P1: 2.0 × 5 = 10.0
        # CTX: 0.3 × 0.5 = 0.15
        # P2: 0.8 × 3 = 2.4
        assert result['total_energy'] == pytest.approx(12.55, abs=0.01)
        assert result['context_switch_energy'] == pytest.approx(0.15, abs=0.01)

    def test_energy_savings_calculation(self):
        """Verify energy savings percentage formula."""
        assert compute_energy_savings(6.0, 10.0) == 40.0
        assert compute_energy_savings(10.0, 10.0) == 0.0
        assert compute_energy_savings(0.0, 10.0) == 100.0

    def test_efficiency_score(self):
        """Higher throughput per energy = better efficiency."""
        score = compute_efficiency_score(0.5, 10.0)
        assert score == 0.05


# ─────────────────────────────────────────────────────────────
#  Performance Change Tests
# ─────────────────────────────────────────────────────────────
class TestPerformance:
    def test_no_change(self):
        """Same metrics should show 0% change."""
        m = {'avg_waiting_time': 5.0}
        assert compute_performance_change(m, m) == 0.0

    def test_positive_degradation(self):
        """AEAS higher wait time = positive degradation."""
        aeas = {'avg_waiting_time': 5.5}
        base = {'avg_waiting_time': 5.0}
        result = compute_performance_change(aeas, base)
        assert result == pytest.approx(10.0)

    def test_negative_improvement(self):
        """AEAS lower wait time = negative (improvement)."""
        aeas = {'avg_waiting_time': 4.0}
        base = {'avg_waiting_time': 5.0}
        result = compute_performance_change(aeas, base)
        assert result == pytest.approx(-20.0)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
