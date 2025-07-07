# File: main.py
# Main script for running RF measurements (LTE, NR5G, STN, SpurSearch)
import logging
import os
import json
import numpy as np
import re
import pandas as pd
from src.measurements.nr5g_fr1 import std_insr_driver as NR5GDriver
from src.measurements.lte import std_insr_driver as LTE
from src.measurements.SubThermalNoise import option_functions as STN
from src.measurements.spur_search import SpurSearch
from src.utils.utils import std_config, std_meas
from src.instruments.bench import bench

# Configure logging to file and console
logger = logging.getLogger(__name__)
log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'project.log')),
        logging.StreamHandler()
    ]
)

results = []
previous_config = None  # Track previous configuration for optimization

def format_frequency(fundamental_ghz):
    if isinstance(fundamental_ghz, (int, float)):
        return f"{fundamental_ghz:.3f} GHz"
    elif isinstance(fundamental_ghz, list):
        return ", ".join(f"{freq:.3f} GHz" for freq in fundamental_ghz)
    elif isinstance(fundamental_ghz, dict) and "range" in fundamental_ghz:
        r = fundamental_ghz["range"]
        return f"range {r['start_ghz']:.3f}–{r['stop_ghz']:.3f} GHz, step {r['step_mhz']} MHz"
    else:
        return str(fundamental_ghz)

def run_nr5g_measurement(test_config, test_set, instr):
    global previous_config
    try:
        freq = test_config["center_frequency_ghz"] * 1e9
        pwr = test_config["power_dbm"]
        rb = test_config.get("resource_blocks", 51)
        rbo = test_config.get("resource_block_offset", 0)
        bw = test_config.get("channel_bandwidth_mhz", 20)
        mod = test_config.get("modulation_type", "QAM256")
        scs = test_config.get("subcarrier_spacing_khz", 30)
        measure_ch_pwr = test_config.get("measure_ch_pwr", True)
        measure_aclr = test_config.get("measure_aclr", True)

        current_config = {
            "resource_blocks": rb,
            "resource_block_offset": rbo,
            "channel_bandwidth_mhz": bw,
            "modulation_type": mod,
            "subcarrier_spacing_khz": scs
        }

        logger.info(f"Starting NR5G test set {test_set}: freq={freq / 1e9:.3f}GHz, pwr={pwr}dBm, "
                    f"rb={rb}, rbo={rbo}, bw={bw}MHz, mod={mod}, scs={scs}kHz")
        timings = {}

        if previous_config != current_config:
            logger.info("Waveform configuration changed, reconfiguring VSA/VSG")
            _, timings["VSG_Config"] = instr.VSG_Config()
            _, timings["VSA_Config"] = instr.VSA_Config()
            previous_config = current_config
        else:
            logger.info("Waveform configuration unchanged, skipping VSA/VSG config")

        instr.VSx_freq(freq=freq)
        instr.VSG_pwr(pwr=pwr)
        config_result, timings["VSA_get_info"] = instr.VSA_get_info()
        config = config_result
        _, timings["VSA_sweep_evm"] = instr.VSA_sweep()
        evm, timings["VSA_get_EVM"] = instr.VSA_get_EVM()
        logger.info(f"NR5G EVM: {evm:.2f} dB")
        ch_pwr = None
        acp_l = acp_u = alt_l = alt_u = None
        if measure_aclr:
            aclr_vals, timings["VSA_get_ACLR"] = instr.VSA_get_ACLR()
            logger.info(f"NR5G ACLR: {aclr_vals}")
            if aclr_vals:
                aclr_parts = aclr_vals.split(',')
                if len(aclr_parts) == 5:
                    ch_pwr, acp_l, acp_u, alt_l, alt_u = map(float, aclr_parts)
        elif measure_ch_pwr:
            ch_pwr = instr.VSA_get_chPwr()
            logger.info(f"NR5G Channel Power: {ch_pwr:.2f} dBm")
        results.append({
            "test_set": test_set,
            "type": "NR5G",
            "center_frequency_hz": freq,
            "power_dbm": pwr,
            "resource_blocks": rb,
            "resource_block_offset": rbo,
            "channel_bandwidth_mhz": bw,
            "modulation_type": mod,
            "subcarrier_spacing_khz": scs,
            "config": config,
            "evm": evm,
            "ch_power": ch_pwr,
            "acp_lower": acp_l,
            "acp_upper": acp_u,
            "alt_lower": alt_l,
            "alt_upper": alt_u,
            "timings": timings
        })
    except Exception as e:
        logger.error(f"NR5G test set {test_set} failed: {e}", exc_info=True)

def run_lte_measurement(test_config, test_set, instr):
    global previous_config
    try:
        freq = test_config["center_frequency_ghz"] * 1e9
        pwr = test_config["power_dbm"]
        rbo = test_config.get("resource_block_offset", 0)
        bw = test_config.get("channel_bandwidth_mhz", 20)
        mod = test_config.get("modulation_type", "QAM256")
        dupl = test_config.get("duplexing", "FDD")
        ldir = test_config.get("link_direction", "UL")
        measure_ch_pwr = test_config.get("measure_ch_pwr", True)
        measure_aclr = test_config.get("measure_aclr", True)
        linkd = "UP" if ldir == "UL" else "DOWN"

        current_config = {
            "resource_block_offset": rbo,
            "channel_bandwidth_mhz": bw,
            "modulation_type": mod,
            "duplexing": dupl,
            "link_direction": ldir
        }

        logger.info(f"Starting LTE test set {test_set}: freq={freq / 1e9:.3f}GHz, pwr={pwr}dBm, "
                    f"rbo={rbo}, bw={bw}MHz, mod={mod}, dupl={dupl}, ldir={ldir}, linkd={linkd}")
        timings = {}

        if previous_config != current_config:
            logger.info("Waveform configuration changed, reconfiguring VSA/VSG")
            _, timings["VSG_Config"] = instr.VSG_Config()
            _, timings["VSA_Config"] = instr.VSA_Config()
            previous_config = current_config
        else:
            logger.info("Waveform configuration unchanged, skipping VSA/VSG config")

        instr.VSx_freq(freq=freq)
        instr.VSG_pwr(pwr=pwr)
        rb = instr.rb
        logger.info(f"Queried resource blocks: {rb}")
        config_result, timings["VSA_get_info"] = instr.VSA_get_info()
        config = config_result
        _, timings["VSA_sweep_evm"] = instr.VSA_sweep()
        evm, timings["VSA_get_EVM"] = instr.VSA_get_EVM()
        logger.info(f"LTE EVM: {evm:.2f} dB")
        ch_pwr = None
        acp_l = acp_u = alt_l = alt_u = None
        if measure_aclr:
            aclr_vals, timings["VSA_get_ACLR"] = instr.VSA_get_ACLR()
            logger.info(f"LTE ACLR: {aclr_vals}")
            if aclr_vals:
                aclr_parts = aclr_vals.split(',')
                if len(aclr_parts) == 5:
                    ch_pwr, acp_l, acp_u, alt_l, alt_u = map(float, aclr_parts)
        elif measure_ch_pwr:
            ch_pwr = instr.VSA_get_chPwr()
            logger.info(f"LTE Channel Power: {ch_pwr:.2f} dBm")
        results.append({
            "test_set": test_set,
            "type": "LTE",
            "center_frequency_hz": freq,
            "power_dbm": pwr,
            "resource_blocks": rb,
            "resource_block_offset": rbo,
            "channel_bandwidth_mhz": bw,
            "modulation_type": mod,
            "duplexing": dupl,
            "link_direction": ldir,
            "config": config,
            "evm": evm,
            "ch_power": ch_pwr,
            "acp_lower": acp_l,
            "acp_upper": acp_u,
            "alt_lower": alt_l,
            "alt_upper": alt_u,
            "timings": timings
        })
    except Exception as e:
        logger.error(f"LTE test set {test_set} failed: {e}", exc_info=True)

def run_spur_search_measurement(test_config, test_set, instr):
    try:
        fundamental_ghz = test_config["fundamental_frequency_ghz"]
        rbw_mhz = test_config.get("rbw_mhz", 0.01)
        spur_limit_dbm = test_config.get("spur_limit_dbm", -95)
        pwr = test_config.get("power_dbm", -70)

        logger.info(f"Starting SpurSearch test set {test_set}: fundamental={format_frequency(fundamental_ghz)}, "
                    f"RBW={rbw_mhz:.3f} MHz, limit={spur_limit_dbm:.2f} dBm, power={pwr:.2f} dBm")
        timings = {}

        _, timings["measure"] = instr.measure()
        results_dict = instr.get_results()
        logger.debug(f"SpurSearch results: {results_dict}")

        local_test_set = test_set

        for freq_ghz, spurs in results_dict.items():
            timings.update(getattr(instr, "timings", {}))
            config = f"{freq_ghz:.3f}GHz_Spur_RBW{rbw_mhz:.3f}MHz_Limit{spur_limit_dbm:.2f}dBm"
            result = {
                "test_set": local_test_set,
                "type": "SpurSearch",
                "fundamental_frequency_hz": float(freq_ghz) * 1e9,
                "rbw_hz": rbw_mhz * 1e6,
                "spur_limit_dbm": spur_limit_dbm,
                "power_dbm": pwr,
                "spurs": [{"frequency_hz": freq_hz, "power_dbm": power_dbm} for freq_hz, power_dbm in spurs],
                "config": config,
                "timings": timings.copy()
            }
            if not spurs:
                result["error"] = "No spurs detected"
            results.append(result)
            local_test_set += 1
        return local_test_set
    except Exception as e:
        logger.error(f"SpurSearch test set {test_set} failed: {e}", exc_info=True)
        results.append({
            "test_set": test_set,
            "type": "SpurSearch",
            "fundamental_frequency_hz": None,
            "rbw_hz": rbw_mhz * 1e6,
            "spur_limit_dbm": spur_limit_dbm,
            "power_dbm": pwr,
            "spurs": [],
            "config": f"Spur_RBW{rbw_mhz:.3f}MHz_Limit{spur_limit_dbm:.2f}dBm",
            "timings": timings,
            "error": str(e)
        })
        return test_set + 1

# Placeholder for run_stn_measurement (implement as needed)
def run_stn_measurement(instr, freq_hz, test_set, iterations=10):
    logger.info(f"STN measurement placeholder for test_set {test_set}, freq {freq_hz}, iterations {iterations}")
    # Add your actual STN measurement logic here

if __name__ == '__main__':
    logger.info("Starting RF measurement script")
    json_path = os.path.join(os.path.dirname(__file__), 'test_inputs.json')
    default_inputs = {
        "lte": [{
            "run": True,
            "center_frequency_ghz": 6.201,
            "power_dbm": [-5.0],
            "resource_block_offset": 0,
            "channel_bandwidth_mhz": 5,
            "modulation_type": "QPSK",
            "duplexing": "TDD",
            "link_direction": "UL",
            "measure_ch_pwr": True,
            "measure_aclr": True
        }],
        "nr5g": [],
        "STN": [{
            "run": True,
            "center_frequency_ghz": 6.321,
            "iterations": 3
        }],
        "spur_search": [{
            "run": True,
            "fundamental_frequency_ghz": 6.0,
            "rbw_mhz": 0.01,
            "spur_limit_dbm": -95,
            "power_dbm": -10.0
        }]
    }
    try:
        with open(json_path, 'r') as f:
            inputs = json.load(f)
        logger.info(f"Loaded test inputs from {json_path}")
    except Exception as e:
        logger.error(f"Error reading JSON file: {e}", exc_info=True)
        print(f"Error reading JSON file: {e}")
        inputs = default_inputs

    logger.debug(f"Test inputs: {json.dumps(inputs, indent=2)}")

    test_set = 1
    for test in inputs.get("lte", []):
        if test.get("run", False):
            logger.debug(f"Processing LTE test: {test}")
            frequencies = test["center_frequency_ghz"] if isinstance(test["center_frequency_ghz"], list) else [
                test["center_frequency_ghz"]]
            try:
                instr = LTE(freq=frequencies[0] * 1e9, pwr=test["power_dbm"][0], rb=None,
                            rbo=test.get("resource_block_offset", 0),
                            bw=test.get("channel_bandwidth_mhz", 20), mod=test.get("modulation_type", "QAM256"),
                            dupl=test.get("duplexing", "FDD"), ldir=test.get("link_direction", "UL"))
                for freq in frequencies:
                    for pwr in test["power_dbm"]:
                        test_config = test.copy()
                        test_config["center_frequency_ghz"] = freq
                        test_config["power_dbm"] = pwr
                        print(f"\n=== Test Set {test_set} (LTE) ===")
                        print(f"LTE Freq: {freq:.3f} GHz, Power: {pwr:.2f} dBm")
                        run_lte_measurement(test_config, test_set, instr)
                        test_set += 1
                LTE.close_connections(self=instr)
            except Exception as e:
                logger.error(f"LTE test initialization failed: {e}", exc_info=True)

    previous_config = None
    instr = None
    for test in inputs.get("nr5g", []):
        if test.get("run", False):
            logger.debug(f"Processing NR5G test: {test}")
            frequencies = test["center_frequency_ghz"] if isinstance(test["center_frequency_ghz"], list) else [
                test["center_frequency_ghz"]]
            try:
                if instr is None:
                    instr = NR5GDriver(freq=frequencies[0] * 1e9, pwr=test["power_dbm"][0],
                                       rb=test.get("resource_blocks", 51),
                                       rbo=test.get("resource_block_offset", 0),
                                       bw=test.get("channel_bandwidth_mhz", 20),
                                       mod=test.get("modulation_type", "QAM256"),
                                       scs=test.get("subcarrier_spacing_khz", 30))
                for freq in frequencies:
                    for pwr in test["power_dbm"]:
                        test_config = test.copy()
                        test_config["center_frequency_ghz"] = freq
                        test_config["power_dbm"] = pwr
                        print(f"\n=== Test Set {test_set} (NR5G) ===")
                        run_nr5g_measurement(test_config, test_set, instr)
                        test_set += 1
            except Exception as e:
                logger.error(f"NR5G test initialization failed: {e}", exc_info=True)

    stn_instr = None
    for test in inputs.get("STN", []):
        if test.get("run", False):
            logger.debug(f"Processing STN test: {test}")
            freq_input = test.get("center_frequency_ghz")
            try:
                if isinstance(freq_input, dict) and "range" in freq_input:
                    range_config = freq_input["range"]
                    start_ghz = range_config.get("start_ghz")
                    stop_ghz = range_config.get("stop_ghz")
                    step_mhz = range_config.get("step_mhz")
                    if None in [start_ghz, stop_ghz, step_mhz]:
                        raise ValueError(f"Missing range parameters: {range_config}")
                    if not all(isinstance(x, (int, float)) for x in [start_ghz, stop_ghz, step_mhz]):
                        raise ValueError(f"Invalid range parameter types: {range_config}")
                    if start_ghz > stop_ghz:
                        raise ValueError(f"Start frequency ({start_ghz} GHz) exceeds stop ({stop_ghz} GHz)")
                    if step_mhz <= 0:
                        raise ValueError(f"Invalid step size: {step_mhz} MHz")
                    num_steps = int((stop_ghz - start_ghz) / (step_mhz / 1000.0)) + 1
                    frequencies = np.linspace(start_ghz, stop_ghz, num_steps).tolist()
                    logger.info(f"Generated {len(frequencies)} frequencies: {frequencies} GHz")
                    if len(frequencies) > 100:
                        logger.warning(f"Large frequency count ({len(frequencies)}). Estimated runtime: "
                                       f"{len(frequencies) * test.get('iterations', 10) * 1.0:.0f}s")
                elif isinstance(freq_input, (list, float, int)):
                    frequencies = freq_input if isinstance(freq_input, list) else [freq_input]
                    logger.info(f"Using discrete frequencies: {frequencies} GHz")
                else:
                    raise ValueError(f"Invalid center_frequency_ghz format: {freq_input}")
            except Exception as e:
                logger.error(f"Failed to process frequency input: {e}", exc_info=True)
                continue

            iterations = test.get("iterations", 10)
            for freq in frequencies:
                logger.info(f"Preparing STN test set {test_set} at {freq:.3f} GHz")
                print(f"\n=== Test Set {test_set} (STN) ===")
                print(f"STN Freq: {freq:.3f} GHz, Iterations: {iterations}")
                try:
                    if stn_instr is None:
                        logger.debug("Initializing new STN instrument")
                        stn_instr = STN(freq=freq * 1e9)
                    else:
                        logger.debug(f"Reusing STN instrument, setting freq to {freq * 1e9:.3f} Hz")
                        stn_instr.STN_set_frequency(freq * 1e9)
                    run_stn_measurement(stn_instr, freq * 1e9, test_set, iterations=iterations)
                    test_set += 1
                except Exception as e:
                    logger.error(f"STN test set {test_set} failed: {e}", exc_info=True)

    spur_instr = None
    for test in inputs.get("spur_search", []):
        if test.get("run", False):
            logger.debug(f"Processing SpurSearch test: {test}")
            try:
                if spur_instr is None:
                    spur_instr = SpurSearch(
                        fundamental_frequency_ghz=test["fundamental_frequency_ghz"],
                        rbw_mhz=test.get("rbw_mhz", 0.01),
                        spur_limit_dbm=test.get("spur_limit_dbm", -95),
                        power_dbm=test.get("power_dbm", -70)
                    )
                print(f"\n=== Test Set {test_set} (SpurSearch) ===")
                test_set = run_spur_search_measurement(test, test_set, spur_instr)
            except Exception as e:
                logger.error(f"SpurSearch test initialization failed: {e}", exc_info=True)

    if instr:
        try:
            NR5GDriver.close_connections()
        except Exception as e:
            logger.error(f"Error closing NR5G connections: {e}", exc_info=True)
    if stn_instr:
        try:
            stn_instr.close_connections()
        except Exception as e:
            logger.error(f"Error closing STN connections: {e}", exc_info=True)
    if spur_instr:
        try:
            spur_instr.close()
        except Exception as e:
            logger.error(f"Error closing SpurSearch connections: {e}", exc_info=True)

    results_path = os.path.join(os.path.dirname(__file__), 'results_output.json')
    try:
        with open(results_path, 'w') as outfile:
            json.dump(results, outfile, indent=2)
        logger.info(f"Saved results to: {results_path}")
    except Exception as e:
        logger.error(f"Error saving JSON results: {e}", exc_info=True)

    if not results:
        logger.warning("No test results generated. Creating empty DataFrame.")
        df = pd.DataFrame(columns=[
            "Test Set", "Type", "Center Frequency (GHz)", "Power (dBm)", "Resource Blocks",
            "Channel Bandwidth (MHz)", "Modulation Type", "EVM (dB)", "EVM Capture Time (s)",
            "CH Power (dBm)", "ACP Lower (dB)", "ACP Upper (dB)", "ACLR Capture Time (s)",
            "Total Test Time (s)", "Config Summary", "VSG_Config Time (s)", "VSA_Config Time (s)",
            "VSA_get_info Time (s)", "Iteration", "Marker (dBm)", "Marker Time (s)", "Stats Avg (dBm)",
            "Fundamental Frequency (GHz)", "RBW (MHz)", "Spur Limit (dBm)", "Spur Frequency (MHz)",
            "Spur Power (dBm)", "Spur Measurement Time (s)", "Error"
        ])
    else:
        rows = []
        total_test_time_sum = 0
        for entry in results:
            if entry["type"] in ["LTE", "NR5G"]:
                timings = entry.get("timings", {})
                total_test_time = sum([
                    timings.get("VSA_sweep_evm", 0),
                    timings.get("VSA_get_EVM", 0),
                    timings.get("VSA_get_ACLR", 0)
                ])
                total_test_time_sum += total_test_time
                base = {
                    "Test Set": entry["test_set"],
                    "Type": entry["type"],
                    "Center Frequency (GHz)": entry["center_frequency_hz"] / 1e9,
                    "Power (dBm)": entry.get("power_dbm"),
                    "Resource Blocks": entry.get("resource_blocks"),
                    "Channel Bandwidth (MHz)": entry.get("channel_bandwidth_mhz"),
                    "Modulation Type": entry.get("modulation_type"),
                    "EVM (dB)": entry.get("evm"),
                    "EVM Capture Time (s)": timings.get("VSA_sweep_evm", 0),
                    "CH Power (dBm)": entry.get("ch_power"),
                    "ACP Lower (dB)": entry.get("acp_lower"),
                    "ACP Upper (dB)": entry.get("acp_upper"),
                    "ACLR Capture Time (s)": timings.get("VSA_get_ACLR", 0),
                    "Total Test Time (s)": total_test_time,
                    "Config Summary": entry.get("config"),
                    "VSG_Config Time (s)": timings.get("VSG_Config", 0),
                    "VSA_Config Time (s)": timings.get("VSA_Config", 0),
                    "VSA_get_info Time (s)": timings.get("VSA_get_info", 0)
                }
                rows.append(base)
            elif entry["type"] == "STN":
                markers = entry.get("markers", [])
                stats = entry.get("stats", None)
                total_test_time = sum(m["meas_time"] for m in markers)
                total_test_time_sum += total_test_time
                stats_dict = {}
                if stats:
                    matches = re.findall(r"(Min|Max|Avg|StdDev|Delta):([-+]?\d+\.\d+)", stats)
                    for key, value in matches:
                        stats_dict[key] = float(value)
                for i, marker in enumerate(markers, 1):
                    base = {
                        "Test Set": entry["test_set"],
                        "Type": entry["type"],
                        "Iteration": i,
                        "Center Frequency (GHz)": entry["center_frequency_hz"] / 1e9,
                        "Marker (dBm)": marker["marker"],
                        "Marker Time (s)": marker["meas_time"],
                        "Stats Avg (dBm)": stats_dict.get("Avg"),
                        "Total Test Time (s)": total_test_time if i == 1 else None,
                        "Config Summary": entry.get("config"),
                        "VSA_Config Time (s)": entry["timings"].get("VSA_Config", 0) if i == 1 else None
                    }
                    if "error" in entry:
                        base["Error"] = entry["error"]
                    rows.append(base)
            elif entry["type"] == "SpurSearch":
                timings = entry.get("timings", {})
                total_test_time = sum(timings.values())
                total_test_time_sum += total_test_time
                spurs = entry.get("spurs", [])
                if spurs:
                    for i, spur in enumerate(spurs, 1):
                        base = {
                            "Test Set": entry["test_set"],
                            "Type": entry["type"],
                            "Fundamental Frequency (GHz)": entry["fundamental_frequency_hz"] / 1e9,
                            "RBW (MHz)": entry["rbw_hz"] / 1e6,
                            "Spur Limit (dBm)": entry["spur_limit_dbm"],
                            "Power (dBm)": entry["power_dbm"],
                            "Spur Frequency (MHz)": spur["frequency_hz"] / 1e6,
                            "Spur Power (dBm)": spur["power_dbm"],
                            "Spur Measurement Time (s)": timings.get(f"get_results_{entry['fundamental_frequency_hz']/1e9}", 0),
                            "Total Test Time (s)": total_test_time if i == 1 else None,
                            "Config Summary": entry.get("config"),
                            "VSA_Config Time (s)": timings.get(f"VSA_config_{entry['fundamental_frequency_hz']/1e9}", 0) if i == 1 else None,
                            "VSG_Config Time (s)": timings.get(f"VSG_config_{entry['fundamental_frequency_hz']/1e9}", 0) if i == 1 else None
                        }
                        if "error" in entry:
                            base["Error"] = entry.get("error")
                        rows.append(base)
                else:
                    base = {
                        "Test Set": entry["test_set"],
                        "Type": entry["type"],
                        "Fundamental Frequency (GHz)": entry["fundamental_frequency_hz"] / 1e9 if entry["fundamental_frequency_hz"] else None,
                        "RBW (MHz)": entry["rbw_hz"] / 1e6,
                        "Spur Limit (dBm)": entry["spur_limit_dbm"],
                        "Power (dBm)": entry["power_dbm"],
                        "Spur Frequency (MHz)": None,
                        "Spur Power (dBm)": None,
                        "Spur Measurement Time (s)": timings.get(f"get_results_{entry['fundamental_frequency_hz']/1e9}", 0) if entry["fundamental_frequency_hz"] else 0,
                        "Total Test Time (s)": total_test_time,
                        "Config Summary": entry.get("config"),
                        "VSA_Config Time (s)": timings.get(f"VSA_config_{entry['fundamental_frequency_hz']/1e9}", 0),
                        "VSG_Config Time (s)": timings.get(f"VSG_config_{entry['fundamental_frequency_hz']/1e9}", 0),
                        "Error": entry.get("error", "No spurs detected")
                    }
                    rows.append(base)
        rows.append({
            "Test Set": "Total",
            "Type": "",
            "Total Test Time (s)": total_test_time_sum,
            "Config Summary": "N/A"
        })
        df = pd.DataFrame(rows)

    if "Center Frequency (GHz)" in df.columns:
        try:
            df["Center Frequency (GHz)"] = df["Center Frequency (GHz)"].map("{:.3f}".format, na_action='ignore')
        except Exception as e:
            logger.error(f"Error formatting Center Frequency column: {e}", exc_info=True)
    if "Fundamental Frequency (GHz)" in df.columns:
        try:
            df["Fundamental Frequency (GHz)"] = df["Fundamental Frequency (GHz)"].map("{:.3f}".format, na_action='ignore')
            df["Spur Frequency (MHz)"] = df["Spur Frequency (MHz)"].map("{:.3f}".format, na_action='ignore')
        except Exception as e:
            logger.error(f"Error formatting Spur columns: {e}", exc_info=True)

    excel_path = os.path.join(os.path.dirname(__file__), 'results_output.xlsx')
    try:
        df.to_excel(excel_path, index=False)
        logger.info(f"Successfully saved to: {excel_path}")
    except Exception as e:
        logger.error(f"Error saving Excel results: {e}", exc_info=True)