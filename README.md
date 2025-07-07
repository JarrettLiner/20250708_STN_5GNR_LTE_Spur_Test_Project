RF Measurement Project
Overview
This project provides Python scripts to control Vector Signal Analyzer (VSA) and Vector Signal Generator (VSG) instruments for RF measurements, including LTE, 5G NR, Sub-Thermal Noise (STN), and Spur Search. Test parameters and execution flags are specified in a JSON file (config/test_inputs.json).
Project Structure
Qorvo_STNoise_LTE_5GNR_meas_with_timing/
├── src/
│   ├── instruments/         # Instrument control classes and config (bench_config.ini)
│   ├── measurements/        # Measurement drivers
│   ├── utils/               # Utility functions
│   ├── main.py              # Main entry point
├── config/
│   ├── test_inputs.json     # User-defined test parameters and execution flags
│   ├── bench_config.ini     # Instrument IP configuration
├── tests/                   # Unit tests
├── scripts/                 # Automation scripts (planned)
├── logs/                    # Log files
├── docs/                    # Documentation
├── requirements.txt         # Dependencies
├── setup.bat                # Windows setup script
├── .gitignore               # Git ignore rules
├── .gitattributes           # Git attributes
└── pyproject.toml           # Project metadata (optional)

Setup

Install Dependencies:
pip install -r requirements.txt

Note: The iSocket library is included in src/instruments/iSocket.py. Alternatively, use pyvisa for instrument communication.

Configure Instruments:

Update config/bench_config.ini with VSA and VSG IP addresses.
Example:[Settings]
VSA_IP = 192.168.200.20
VSG_IP = 192.168.200.10




Configure Test Parameters:

Edit config/test_inputs.json to specify frequencies (in GHz), powers (in dBm), and test execution flags.
The JSON file has four sections: lte, nr5g, STN, and spur_search.
Example:{
  "lte": [
    {
      "run": true,
      "center_frequency_ghz": [6.201, 6.501],
      "power_dbm": [-10.0, -9.0, -8.0, -7.0, -6.0, -5.0],
      "resource_block_offset": 0,
      "channel_bandwidth_mhz": 5,
      "modulation_type": "QPSK",
      "duplexing": "TDD",
      "link_direction": "UL",
      "measure_ch_pwr": true,
      "measure_aclr": true
    }
  ],
  "nr5g": [
    {
      "run": true,
      "center_frequency_ghz": [6.123, 6.223],
      "power_dbm": [-5.0, -1.0],
      "resource_blocks": 51,
      "resource_block_offset": 0,
      "channel_bandwidth_mhz": 20,
      "modulation_type": "QAM256",
      "subcarrier_spacing_khz": 30,
      "measure_ch_pwr": true,
      "measure_aclr": true
    }
  ],
  "STN": [
    {
      "run": true,
      "center_frequency_ghz": {
        "range": {
          "start_ghz": 0.617,
          "stop_ghz": 0.961,
          "step_mhz": 10
        }
      },
      "iterations": 1
    },
    {
      "run": true,
      "center_frequency_ghz": [2.483, 3.300, 3.500],
      "iterations": 1
    }
  ],
  "spur_search": [
    {
      "run": true,
      "fundamental_frequency_ghz": 6.000,
      "rbw_mhz": 0.01,
      "spur_limit_dbm": -95,
      "power_dbm": -10.0
    }
  ]
}


Frequencies: In GHz, as single values, lists, or ranges (e.g., {"range": {"start_ghz": 0.617, "stop_ghz": 0.961, "step_mhz": 10}}).
Power Inputs: Arrays for sweeps (e.g., [-10.0, -9.0, -8.0]).
Run Flags: true/false to enable/disable tests.
Multiple entries with "run": true enable frequency sweeps; power sweeps use arrays.
Ensure numeric frequencies/powers and boolean flags.
Defaults are used if the file is missing or malformed.


Run Measurements:
python src/main.py



Usage

LTE Measurement: Measures LTE signals if "run": true in lte.
5G NR Measurement: Measures 5G NR FR1 signals if "run": true in nr5g.
Sub-Thermal Noise (STN) Measurement: Measures noise power if "run": true in STN.
Spur Search Measurement: Detects spurs if "run": true in spur_search.
Parameter Sweeps:
Frequency sweeps via multiple entries or lists/ranges.
Power sweeps via power_dbm arrays.


Output: Results saved to results_output.json and results_output.xlsx in the project root.

Requirements

Python 3.8+
Libraries: numpy>=1.24.0, pandas>=2.0.0, openpyxl>=3.1.0, iSocket (custom, included)

Notes

Ensure instruments are network-accessible.
Update SCPI commands for different instrument models.
Add tests in tests/ for validation.
Save test_inputs.json with UTF-8 encoding.
Do not track generated files (results_output.json, results_output.xlsx) in version control.

