# File: src/measurements/lte.py
import logging
import os
import numpy as np
from src.utils.utils import method_timer
from src.instruments.bench import bench

logger = logging.getLogger(__name__)


class std_insr_driver:
    """Class for LTE measurements with VSA and VSG."""

    def __init__(self, freq=6e9, pwr=-10.0, rb=None, rbo=0, bw=20, dupl="FDD", mod="QAM256", ldir="UP", linkd="UP"):
        """Initialize LTE driver and connections.

        Args:
            freq (float): Center frequency in Hz, default 6e9.
            pwr (float): Power in dBm, default -10.0.
            rb (int, optional): Resource blocks, default None (queried later).
            rbo (int): Resource block offset, default 0.
            bw (int): Channel bandwidth in MHz, default 20.
            dupl (str): Duplexing mode, default "FDD".
            mod (str): Modulation type, default "QAM256".
            ldir (str): Link direction, default "UP".
            linkd (str): Link direction for VSG, default "UP".
        """
        logger.info(
            f"Initializing LTE driver with freq={freq / 1e9:.3f}GHz, pwr={pwr}dBm, rbo={rbo}, bw={bw}MHz, dupl={dupl}, mod={mod}, ldir={ldir}, linkd={linkd}")
        self.VSA = bench().VSA_start()  # Start VSA connection
        self.VSG = bench().VSG_start()  # Start VSG connection
        self.freq = freq
        self.pwr = pwr
        self.rb = rb if rb else 100
        self.rbo = rbo
        self.bw = bw
        self.dupl = dupl
        self.mod = mod
        self.ldir = ldir
        self.linkd = linkd
        self.swp_time = 0.01

    @method_timer
    def VSG_Config(self):
        """Configure VSG for LTE signal generation."""
        logger.info("Configuring VSG for LTE")
        self.VSG.query('*RST;*OPC?')  # Reset VSG
        self.VSG.write(f':SOUR:FREQ:CW {self.freq}')  # Set frequency
        self.VSG.write(':SOUR1:BB:EUTR:STDM LTE')  # Set LTE standard
        self.VSG.write(f':SOUR1:BB:EUTR:DUPL {self.dupl}')  # Set duplexing
        self.VSG.write(f':SOUR1:BB:EUTR:LINK {self.linkd}')  # Set link direction
        bw_map = {5: 'BW5_00', 20: 'BW20_00'}
        self.VSG.write(f':SOUR1:BB:EUTR:UL:BW {bw_map.get(self.bw, "BW20_00")}')  # Set bandwidth
        self.rb = int(self.VSG.query(':SOURce1:BB:EUTRa:UL:NORB?'))  # Query resource blocks
        logger.info(f"Queried resource blocks: {self.rb}")
        self.VSG.write(f':SOUR1:BB:EUTR:UL:CELL0:SUBF0:ALL0:PUSC:SET1:RBC {self.rb}')  # Set resource block count
        self.VSG.write(f':SOUR1:BB:EUTR:UL:CELL0:SUBF0:ALL0:PUSC:SET1:VRB {self.rbo}')  # Set resource block offset
        self.VSG.write(f':SOUR1:BB:EUTR:UL:CELL0:SUBF0:ALL0:CW1:PUSC:MOD {self.mod}')  # Set modulation
        self.VSG.write(':SOUR1:BB:EUTR:STAT 1')  # Enable LTE signal
        self.VSG.query(f':SOUR1:POW:LEV:IMM:AMPL {self.pwr};*OPC?')  # Set power
        self.VSG.write(':OUTP1:STAT 1')  # Enable output
        self.VSG.query(':SOUR1:CORR:OPT:EVM 1;*OPC?')  # Optimize EVM
        self.VSG.write(':SOUR1:BB:EUTR:TRIG:OUTP1:MODE REST')  # Set trigger mode
        self.VSG.write('*OPC?')  # Wait for operation complete

    @method_timer
    def VSG_freq(self, freq):
        """Set VSG frequency.

        Args:
            freq (float): Frequency in Hz.
        """
        logger.info(f"Setting VSG frequency to {freq / 1e9:.3f}GHz")
        self.VSG.write(f':SOUR:FREQ:CW {freq}')
        self.freq = freq

    @method_timer
    def VSG_pwr(self, pwr):
        """Set VSG output power.

        Args:
            pwr (float): Power in dBm.
        """
        logger.info(f"Setting VSG power to {pwr} dBm")
        self.VSG.query(f':SOUR1:POW:LEV:IMM:AMPL {pwr};*OPC?')
        self.pwr = pwr

    @method_timer
    def VSA_Config(self):
        """Configure VSA for LTE measurement."""
        logger.info("Configuring VSA for LTE")
        self.VSA.query('*RST;*OPC?')  # Reset VSA
        self.VSA.query(':INST:SEL "LTE";*OPC?')  # Select LTE mode
        self.VSA.write(f':SENS:FREQ:CENT {self.freq}')  # Set center frequency
        self.VSA.write(':INP:ATT:AUTO OFF')  # Disable auto attenuation
        self.VSA.write(':INP:ATT 10')  # Set 10 dB attenuation
        self.VSA.write(':TRIG:SEQ:SOUR EXT')  # Set external trigger
        self.VSA.write(f':CONF:LTE:LDIR {self.ldir}')  # Set link direction
        self.VSA.write(f':CONF:LTE:DUPL {self.dupl}')  # Set duplexing
        bw_map = {5: 'BW5_00', 20: 'BW20_00'}
        self.VSA.write(f':CONF:LTE:UL:CC:BW {bw_map.get(self.bw, "BW20_00")};*OPC')  # Set bandwidth
        self.VSA.write(f':CONF:LTE:UL:CC:SUBF2:ALL:MOD {self.mod}')  # Set modulation
        # Conditionally set single subframe analysis based on modulation type
        if self.mod == "QPSK":
            self.VSA.write(':SENS:LTE:FRAM:SSUB OFF')  # Disable single subframe analysis
            logger.info("Single subframe analysis disabled for QPSK")
        else:
            self.VSA.write(':SENS:LTE:FRAM:SSUB ON')  # Enable single subframe analysis
            logger.info("Single subframe analysis enabled for non-QPSK modulation")
        self.VSA.write(':UNIT:EVM DB')  # Set EVM unit to dB
        self.VSA.write('INIT:CONT OFF')  # Disable continuous sweep
        self.VSA.clear_error()  # Clear error queue

    @method_timer
    def VSx_freq(self, freq):
        """Set frequency for both VSA and VSG.

        Args:
            freq (float): Frequency in Hz.
        """
        logger.info(f"Setting VSA/VSG frequency to {freq / 1e9:.3f}GHz")
        self.VSA.write(f':SENS:FREQ:CENT {freq}')
        self.VSG.write(f':SOUR:FREQ:CW {freq}')
        self.freq = freq

    @method_timer
    def VSA_sweep(self):
        """Perform VSA sweep for measurement."""
        logger.info("Performing VSA sweep")
        self.VSA.write('INIT:CONT OFF')  # Disable continuous sweep
        self.VSA.query('INIT:IMM;*OPC?')  # Initiate sweep and wait

    @method_timer
    def VSA_get_info(self):
        """Get and return VSA configuration info."""
        config = f"{self.freq / 1e9:.3f}GHz_{self.bw}MHz_{self.dupl}_{self.ldir}_15kHz_{self.rb}RB_{self.rbo}RBO_{self.mod}"
        logger.info(f"VSA configuration: {config}")
        return config

    @method_timer
    def VSA_level(self):
        """Placeholder for VSA level adjustment."""
        pass

    @method_timer
    def VSA_get_EVM(self):
        """Measure and return EVM (Error Vector Magnitude).

        Returns:
            float: EVM value in dB.
        """
        logger.info("Measuring EVM")
        try:
            self.VSA.query('INIT:IMM;*OPC?')  # Perform sweep
            evm = self.VSA.queryFloat(':FETC:CC1:SUMM:EVM:ALL:AVER?')  # Fetch EVM
            logger.info(f"EVM measured: {evm:.2f} dB")
            print(f'EVM measured: {evm:.2f} dB')
            return evm
        except Exception as e:
            logger.error(f"EVM measurement failed: {e}")
            return float('nan')

    @method_timer
    def VSA_get_ACLR(self):
        """Measure and return ACLR (Adjacent Channel Leakage Ratio).

        Returns:
            str: ACLR measurement results.
        """
        logger.info("Measuring ACLR")
        self.VSA.write(':CONF:LTE:MEAS ACLR')  # Configure ACLR measurement
        self.VSA.write(f':SENS:FREQ:CENT {self.freq};*OPC')  # Set frequency
        logger.info(f"Set VSA frequency to {self.freq / 1e9:.3f}GHz for ACLR measurement")
        self.VSA_sweep()  # Perform sweep
        aclr = self.VSA.query(':CALC:MARK:FUNC:POW:RES? ACP')  # Fetch ACLR
        logger.info(f"ACLR measured: {aclr}")
        self.VSA.write(':CONF:LTE:MEAS EVM')  # Revert to EVM measurement
        print(f'ACLR measured: {aclr}')
        return aclr

    @staticmethod
    def VSA_get_chPwr():
        """Placeholder for channel power measurement.

        Returns:
            float: NaN (not implemented).
        """
        logger.info("Measuring channel power")
        return float('nan')

    def __del__(self):
        """Destructor to close sockets."""
        logger.info("Closing sockets")
        if hasattr(self, 'VSA'):
            self.VSA.close()
        if hasattr(self, 'VSG'):
            self.VSG.close()

    @method_timer
    def close_connections(self):
        """Close VSA and VSG connections."""
        logger.info("Closing VSA and VSG connections")
        self.VSA.close()
        self.VSG.close()
        logger.info("Connections closed successfully")