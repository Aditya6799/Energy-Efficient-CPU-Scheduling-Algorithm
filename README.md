# AEAS — Adaptive Energy-Aware CPU Scheduler

> Energy-Efficient CPU Scheduling Algorithm for Mobile & Embedded Systems

## Overview

This project implements the **Adaptive Energy-Aware Scheduler (AEAS)**, a novel CPU scheduling algorithm that minimizes energy consumption through **Dynamic Voltage and Frequency Scaling (DVFS)** while maintaining performance degradation within a strict **≤ 5% threshold**.

## Key Features

- **Custom AEAS Algorithm** — Adaptive process classification using median-based thresholds
- **DVFS Integration** — Dynamic frequency assignment (HIGH/MEDIUM/LOW) based on process class and system load
- **Starvation Prevention** — Automatic frequency boosting for long-waiting processes
- **4 Baseline Comparisons** — FCFS, SJF, Round Robin, Priority Scheduling
- **Interactive Dashboard** — Real-time simulation with Plotly.js charts
- **Formal Evaluation** — Energy savings quantification with performance constraint verification

## Algorithm Design

Each process P_i = (AT_i, BT_i, Pri_i) is classified dynamically:

| Classification | Condition | Frequency | Power |
|---|---|---|---|
| **CRITICAL** | Priority ≤ 2 | HIGH | 2.0 W |
| **SHORT** | BT ≤ median(BT) | MEDIUM | 0.8 W |
| **LONG** | Others | LOW | 0.3 W |

### DVFS Adjustment Rules
- Queue > 5 processes → Force non-critical to LOW
- Queue > 3 processes → Reduce non-critical by one level
- Wait time > threshold → Boost frequency (starvation prevention)

## Project Structure

```
├── app.py                        # Flask server (API routes)
├── scheduler/
│   ├── energy_scheduler.py       # AEAS algorithm (main logic)
│   ├── base_algorithms.py        # FCFS, SJF, RR, Priority
│   └── utils.py                  # Helper functions
├── energy/
│   ├── energy_model.py           # Power model + energy calculations
│   └── dvfs.py                   # DVFS logic and frequency assignment
├── frontend/
│   ├── index.html                # Dashboard UI
│   ├── style.css                 # UI styling
│   └── app.js                    # Frontend logic + API calls
├── tests/
│   ├── test_scheduler.py         # Algorithm tests
│   └── test_energy.py            # Energy model tests
├── data/
│   └── sample_inputs.json        # Predefined test cases
├── requirements.txt
└── README.md
```

## Installation & Setup

```bash
# Optional: create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/simulate` | Run AEAS simulation |
| POST | `/api/compare` | AEAS vs all baseline algorithms |
| POST | `/api/evaluate` | Full evaluation with recommendation |

### Example Request Body

```json
{
  "processes": [
    { "id": "P1", "arrival_time": 0, "burst_time": 6, "priority": 1 },
    { "id": "P2", "arrival_time": 1, "burst_time": 3, "priority": 4 }
  ],
  "dvfs_enabled": true,
  "context_switch_time": 0.5
}
```

### Example API Calls

Run an AEAS simulation:

```bash
curl -X POST http://127.0.0.1:5000/api/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "processes": [
      { "id": "P1", "arrival_time": 0, "burst_time": 6, "priority": 1 },
      { "id": "P2", "arrival_time": 1, "burst_time": 3, "priority": 4 }
    ],
    "dvfs_enabled": true,
    "context_switch_time": 0.5
  }'
```

Compare AEAS against the baseline algorithms:

```bash
curl -X POST http://127.0.0.1:5000/api/compare \
  -H "Content-Type: application/json" \
  -d '{
    "processes": [
      { "id": "P1", "arrival_time": 0, "burst_time": 6, "priority": 1 },
      { "id": "P2", "arrival_time": 1, "burst_time": 3, "priority": 4 }
    ],
    "dvfs_enabled": true,
    "context_switch_time": 0.5
  }'
```

## Running Tests

```bash
pytest tests/ -v
```

## Energy Model

```
E = P(f) × t

Power Levels:
  HIGH   → 2.0 W  (Critical tasks)
  MEDIUM → 0.8 W  (Short tasks)
  LOW    → 0.3 W  (Long/background tasks)
  IDLE   → 0.1 W  (CPU idle)
```

## Evaluation Criteria

- **Energy Reduction**: ≥ 20–40% compared to baselines
- **Performance Loss**: ≤ 5% (strict constraint)
- **Efficiency Score**: throughput / total energy

## Conclusion

AEAS reduces energy consumption significantly while maintaining acceptable performance, making it suitable for mobile and embedded systems where power efficiency is critical.
