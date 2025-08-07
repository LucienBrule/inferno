# Cooling Tools CLI Guide

## Overview

The Cooling Tools CLI provides a set of commands to help estimate and analyze cooling requirements for data center racks.

It supports several calculation modes, including by-circuit, by-load, and measured cooling, allowing for flexible and accurate cooling assessments.

## Command Structure

```
cooling <mode> [OPTIONS]
```

- `<mode>`: The calculation mode to use (`by-circuit`, `by-load`, or `measured`).
- `[OPTIONS]`: Optional flags and arguments to customize the calculation.

## Subcommands

### 1. `by-circuit`

**Description:**  
Estimates cooling requirements based on the electrical circuit configuration of racks (i.e., the maximum theoretical
power draw from the circuits).

**Usage:**

```
cooling by-circuit [--headroom <percent>] [--ups-efficiency <float>]
```

- `--headroom <percent>`: Adds a percentage headroom to the calculated cooling requirement (e.g., `--headroom 10` for
  10% extra).
- `--ups-efficiency <float>`: Specify the UPS efficiency as a decimal (e.g., `--ups-efficiency 0.95`).

**Example:**

```
cooling by-circuit --headroom 15 --ups-efficiency 0.94
```

**Example Output:**

```
Estimated cooling requirement (by circuit): 42.3 kW (with 15% headroom, UPS efficiency: 0.94)
```

---

### 2. `by-load`

**Description:**  
Estimates cooling requirements based on actual or budgeted rack power usage, allowing for more realistic cooling
planning.

**Usage:**

```
cooling by-load [--headroom <percent>] [--ups-efficiency <float>] [--budget-path <path>]
```

- `--headroom <percent>`: Adds a percentage headroom to the calculated cooling requirement.
- `--ups-efficiency <float>`: Specify the UPS efficiency as a decimal.
- `--budget-path <path>`: Path to a rack power budget YAML file. If not specified, defaults to
  `doctrine/power/rack-power-budget.yaml`.

**Example:**

```
cooling by-load --headroom 10 --budget-path configs/custom-power-budget.yaml
```

**Example Output:**

```
Estimated cooling requirement (by load): 36.8 kW (with 10% headroom, using configs/custom-power-budget.yaml)
```

---

### 3. `measured`

**Description:**  
Calculates cooling requirements based on measured power usage data, providing the most accurate results when up-to-date
measurements are available.

**Usage:**

```
cooling measured [--headroom <percent>] [--ups-efficiency <float>]
```

- `--headroom <percent>`: Adds a percentage headroom.
- `--ups-efficiency <float>`: Specify the UPS efficiency as a decimal.

**Example:**

```
cooling measured --headroom 5
```

**Example Output:**

```
Estimated cooling requirement (measured): 33.2 kW (with 5% headroom)
```

---

## Examples

1. **Estimate by circuit with default settings:**
    ```bash
    uv run inferno-cli tools cooling by-circuit
    ```
   ```text
    Inferno Cooling Estimator

    feed-west: 26,702 BTU/hr → 2.2 tons
    feed-east: 26,702 BTU/hr → 2.2 tons
    feed-north: 26,702 BTU/hr → 2.2 tons
    feed-crypt: 26,702 BTU/hr → 2.2 tons

    Total: 106,810 BTU/hr → 8.9 tons

    Note: by-circuit = 240V/30A @ 80% load, 92% UPS eff., +25% headroom.
    by-load = modeled rack watts from doctrine/power/rack-power-budget.yaml (+25% headroom).
    ```
2. **Estimate by load using the default budget file and 10% headroom:**
    ```bash
    uv run inferno-cli tools cooling by-load --headroom 1.1
    ```
    ```text
    Inferno Cooling Estimator

    feed-west: 10,321 BTU/hr → 0.9 tons
    feed-east: 3,565 BTU/hr → 0.3 tons
    feed-north: 7,506 BTU/hr → 0.6 tons
    feed-crypt: 10,508 BTU/hr → 0.9 tons

    Total: 31,902 BTU/hr → 2.7 tons

    Note: by-circuit = 240V/30A @ 80% load, 92% UPS eff., +10% headroom.
    by-load = modeled rack watts from doctrine/power/rack-power-budget.yaml (+10% headroom).
    ```
3. **Estimate by load with a custom budget file:**
    ```bash
    uv run inferno-cli tools cooling by-load --budget-path configs/my-budget.yaml
    ```
4. **Estimate from measured data with custom UPS efficiency:**
    ```bash
    uv run inferno-cli tools cooling measured --ups-efficiency 0.97
    ```
    ```text
    Measured mode not yet implemented — planned SNMP/Redfish integration.
    ```

## Notes

- The `by-load` mode uses the canonical power budget file at `doctrine/power/rack-power-budget.yaml` unless a different
  path is provided via `--budget-path`.
- The `--headroom` flag is optional in all modes and can be used to pad your cooling estimate for safety.
- The `--ups-efficiency` flag lets you account for UPS losses in your cooling estimate.
- Outputs are in kilowatts (kW) and include a summary of the applied options.
- For best results, use the `measured` mode when up-to-date power usage data is available.