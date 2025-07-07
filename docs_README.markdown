# RF Measurement Project

## Overview
This project provides Python scripts to control Vector Signal Analyzer (VSA) and Vector Signal Generator (VSG) instruments for RF measurements, including 5G NR, LTE, and subharmonic analyses. Test parameters and execution flags are specified in a JSON file (`test_inputs.json`).

## Project Structure
```
Qorvo_STNoise_LTE_5GNR_meas_with_timing/
├── src/
│   ├── instruments/         # Instrument control classes and config (bench_config.ini)
│   ├── measurements/        # Measurement drivers
│   ├── utils/               # Utility functions
│   ├── main.py              # Main entry point
│   └── test_inputs.json     # User-defined test parameters and execution flags
├── tests/                   # Unit tests (planned)
├── scripts/                 # Automation scripts (planned)
├── docs/                    # Documentation
├── requirements.txt         # Dependencies
└── pyproject.toml           # Project metadata (optional)
```

## Setup
1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   Note: The `iSocket` library is assumed to be available in `src/instruments/iSocket.py`. Alternatively, use `pyvisa` for instrument communication.

2. **Configure Instruments**:
   - Update `src/instruments/bench_config.ini` with VSA and VSG IP addresses.
   - Example:
     ```ini
     [Settings]
     VSA_IP = 192.168.200.20
     VSG_IP = 192.168.200.10
     ```

     3. **Configure Test Parameters**:
        - Edit `src/test_inputs.json` to specify frequencies (in GHz), powers (in dBm), and test execution flags.
        - The JSON file has three sections: `lte`, `nr5g`, and `subthermalnoise`.
     - **Structure**:
       ```json
       {
         "lte": [
           {
             "run": true,
             "center_frequency_ghz": 6.543,
             "power_dbm": [-10.0, -8.0, -6.0, -4.0, -2.0, 0.0, 2, 4, 6],
             "resource_blocks": 100,
             "resource_block_offset": 0,
             "channel_bandwidth_mhz": 20,
             "modulation_type": "QAM256",
             "duplexing": "FDD",
             "link_direction": "UL"
           },
           {
             "run": false,
             "center_frequency_ghz": 6.100,
             "power_dbm": [-8.0, -7.0, -6.0],
             "resource_blocks": 50,
             "resource_block_offset": 0,
             "channel_bandwidth_mhz": 10,
             "modulation_type": "QAM64",
             "duplexing": "FDD",
             "link_direction": "UL"
           }
         ],
         "nr5g": [
           {
             "run": true,
             "center_frequency_ghz": 6.000,
             "power_dbm": [-10.0, -8.0, -6.0, -4.0, -2.0, 0.0, 2, 4, 6],
             "resource_blocks": 51,
             "resource_block_offset": 0,
             "channel_bandwidth_mhz": 20,
             "modulation_type": "QAM256",
             "transform_precoding": "OFF",
             "direction": "UL",
             "subcarrier_spacing_khz": 30
           },
           {
             "run": false,
             "center_frequency_ghz": 6.987,
             "power_dbm": [-8.0, -7.0, -6.0, -5.0],
             "resource_blocks": 106,
             "resource_block_offset": 0,
             "channel_bandwidth_mhz": 40,
             "modulation_type": "QAM64",
             "transform_precoding": "ON",
             "direction": "DL",
             "subcarrier_spacing_khz": 30
           }
         ],
         "subthermalnoise": [
           {
             "run": true,
             "center_frequency_ghz": 6.321,
             "iterations": 5
           },
           {
             "run": false,
             "center_frequency_ghz": 6.009,
             "iterations": 1
           }
         ],
         "spur_search": [
          {
            "run": true,
            "fundamental_frequency_ghz": 6.0,
            "rbw_mhz": 0.01,
            "spur_limit_dbm": -95,
            "power_dbm": -10.0
          }
        ]
       }
       ```
       - **Frequencies**: In GHz, with 3 decimal places (e.g., `6.000`).
       - **Power Inputs** (for LTE and 5G): Array of values (e.g., `[-10.0, -8.0, -6.0]`).
       - **Run Flags**: Use `true`/`false` to enable/disable tests.
       - Multiple entries with `"run": true` allow frequency sweeps; power sweeps use arrays.
       - Ensure frequencies and powers are numeric, and run flags are boolean.
       - The script uses default parameters if the file is missing or malformed.

4. **Run Measurements**:
   ```bash
   python src/main.py
   ```

## Usage
- **5G NR Measurement**: Configures and measures 5G NR FR1 signals with user-specified frequency and power(s), if `"run": true` in `nr5g`.
- **LTE Measurement**: Configures and measures LTE signals with user-specified frequency and power(s), if `"run": true` in `lte`.
- **Subthermalnoise Measurement**: Measures noise markers in spectrum mode with user-specified frequency, if `"run": true` in `subthermalnoise`.
- **Parameter Sweeps**:
  - Add multiple entries with `"run": true` to sweep frequency.
  - Use arrays for power sweeps (e.g., `[-10.0, -8.0, -6.0, ..., 6.0]`).
- **Output**: Results are saved to `results_output.json` and `results_output.xlsx` in the `src/` directory.

## Requirements
- Python 3.8+
- Libraries: `numpy`, `pandas`, `openpyxl`, `iSocket` (or `pyvisa`)

## Notes
- Ensure instruments are accessible via the network.
- Update SCPI commands if using different instrument models.
- Add tests in `tests/` for validation.
- The `test_inputs.json` file must be in the `src/` directory with the correct structure.
- Invalid JSON entries (e.g., non-numeric frequencies, invalid power arrays, or invalid booleans) trigger default parameters.
- Save the JSON file with UTF-8 encoding to avoid formatting issues.
- Generated files (`results_output.json`, `results_output.xlsx`) should not be tracked in version control.