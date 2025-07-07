# File: src/measurements/nr5g_fr1.py
import logging
import time
from src.utils.utils import method_timer
from src.instruments.bench import bench

logger = logging.getLogger(__name__)


class std_insr_driver:
    """Class for NR5G FR1 measurements with VSA and VSG."""

    _vsa_instance = None  # Class variable for VSA connection
    _vsg_instance = None  # Class variable for VSG connection

    def __init__(self, freq=6e9, pwr=-10.0, rb=51, rbo=0, bw=20, mod="QAM256", scs=30, dupl="FDD", ldir="UP"):
        """Initialize instrument connections and parameters.

        Args:
            freq (float): Center frequency in Hz, default 6e9.
            pwr (float): Power in dBm, default -10.0.
            rb (int): Resource blocks, default 51.
            rbo (int): Resource block offset, default 0.
            bw (int): Channel bandwidth in MHz, default 20.
            mod (str): Modulation type, default "QAM256".
            scs (int): Subcarrier spacing in kHz, default 30.
            dupl (str): Duplexing mode, default "FDD".
            ldir (str): Link direction, default "UP".
        """
        logger.info(f"Initializing NR5G driver with freq={freq / 1e9:.3f}GHz, pwr={pwr}dBm, "
                    f"rb={rb}, rbo={rbo}, bw={bw}MHz, mod={mod}, scs={scs}kHz")
        # Create VSA connection if not exists
        if std_insr_driver._vsa_instance is None:
            std_insr_driver._vsa_instance = bench().VSA_start()
            std_insr_driver._vsa_instance.sock.settimeout(30)
            logger.info("Created new VSA connection")
            std_insr_driver._vsa_instance.query('*IDN?')  # Initial verification
        # Create VSG connection if not exists
        if std_insr_driver._vsg_instance is None:
            std_insr_driver._vsg_instance = bench().VSG_start()
            logger.info("Created new VSG connection")
            std_insr_driver._vsg_instance.query('*IDN?')  # Initial verification
        self.VSA = std_insr_driver._vsa_instance
        self.VSG = std_insr_driver._vsg_instance
        self.freq = freq
        self.pwr = pwr
        self.rb = rb
        self.rbo = rbo
        self.bw = bw
        self.mod = mod
        self.scs = scs
        self.dupl = dupl
        self.ldir = ldir
        self.swp_time = 0.015

    @classmethod
    def close_connections(cls):
        """Close VSA and VSG connections."""
        if cls._vsa_instance:
            cls._vsa_instance.sock.close()
            cls._vsa_instance = None
            logger.info("Closed VSA socket")
        if cls._vsg_instance:
            cls._vsg_instance.sock.close()
            cls._vsg_instance = None
            logger.info("Closed VSG socket")

    @method_timer
    def VSG_Config(self):
        """Configure VSG for 5G NR signal generation."""
        self.VSG.write(f':SOUR1:BB:NR5G:LINK {self.ldir}')  # Set link direction
        self.VSG.write(f':SOUR1:BB:NR5G:QCKS:GEN:DUPL {self.dupl}')  # Set duplexing
        self.VSG.write(':SOUR1:BB:NR5G:QCKS:GEN:CARD FR1GT3')  # Set carrier type
        self.VSG.write(f':SOUR1:BB:NR5G:QCKS:GEN:CBW BW{self.bw}')  # Set channel bandwidth
        self.VSG.write(f':SOUR1:BB:NR5G:QCKS:GEN:SCSP SCS{self.scs}')  # Set subcarrier spacing
        self.VSG.write(f':SOUR1:BB:NR5G:QCKS:GEN:ES:MOD {self.mod}')  # Set modulation
        self.VSG.write(f':SOUR1:BB:NR5G:QCKS:GEN:ES:RBN {self.rb}')  # Set resource blocks
        self.VSG.write(f':SOUR1:BB:NR5G:QCKS:GEN:ES:RBOF {self.rbo}')  # Set resource block offset
        self.VSG.write(':SOUR1:BB:NR5G:QCKS:APPL')  # Apply settings
        self.VSG.write(':SOUR1:BB:NR5G:STAT 1')  # Enable NR5G signal
        self.VSG.write(':OUTP1:STAT 1')  # Enable output
        self.VSG.query(':SOUR1:CORR:OPT:EVM 1;*OPC?')  # Optimize EVM
        self.VSG.write(':SOUR1:BB:NR5G:TRIG:OUTP1:MODE REST')  # Set trigger mode
        self.VSG.write(':SOUR1:BB:NR5G:NODE:RFPH:MODE 0')  # Disable RF phase compensation
        self.VSG_pwr(self.pwr)  # Set power
        self.VSG.query('*OPC?')  # Wait for operation complete
        print('VSG configuration complete.')

    def VSG_pwr(self, pwr):
        """Set VSG output power.

        Args:
            pwr (float): Power in dBm.
        """
        self.VSG.write(f':SOUR1:POW:POW {pwr}')

    @method_timer
    def VSA_Config(self, freq=None, pwr=None):
        """Configure VSA for 5G NR measurement.

        Args:
            freq (float, optional): Override frequency in Hz.
            pwr (float, optional): Override power in dBm.
        """
        logger.info("Configuring VSA for 5G NR")
        self.VSA.query('*RST;*OPC?')  # Reset VSA
        self.VSA.query(':SYST:DISP:UPD ON;*OPC?')  # Enable display updates
        self.VSA.query(':INST:CRE:NEW NR5G, "5G NR";*OPC?')  # Select 5G NR mode
        self.VSA.write('CONF:GEN:IPC:ADDR "192.168.200.10"')  # Set generator IP
        self.VSA.query('CONF:GEN:CONN:STAT ON;*OPC?')  # Enable generator connection
        self.VSA.write('CONF:GEN:CONT:STAT ON')  # Enable continuous generation
        self.VSA.write('CONF:GEN:RFO:STAT ON')  # Enable RF output
        self.VSA.write(f'SENS:FREQ:CENT {self.freq}')  # Set center frequency
        self.VSA.write('CONF:GEN:FREQ:CENT:SYNC:STAT ON')  # Enable frequency sync
        self.VSA.write(':INP:ATT:AUTO OFF')  # Disable auto attenuation
        self.VSA.write(':INP:ATT 10')  # Set 10 dB attenuation
        self.VSA.write('CONF:SETT:RF')  # Configure RF settings
        self.VSA.write('CONF:SETT:NR5G;*OPC?')  # Configure NR5G settings
        self.VSA.write(':TRIG:SEQ:SOUR EXT')  # Set external trigger
        self.VSA.write(':TRIG:EXT:DEL 0')  # Set trigger delay to 0
        self.VSA.write(':SENS:NR5G:FRAM:COUN:AUTO OFF')  # Disable auto frame count
        self.VSA.write(':SENS:NR5G:FRAM:COUN 1')  # Set frame count to 1
        self.VSA.write(':SENS:NR5G:FRAM:SLOT 1')  # Set slot count to 1
        self.VSA.write(':UNIT:EVM DB')  # Set EVM unit to dB
        self.VSA.write(f':SENS:SWE:TIME {self.swp_time}')  # Set sweep time
        self.VSA.write(':CONF:NR5G:MEAS EVM;*OPC')  # Configure EVM measurement
        self.VSA.write(':CONF:NR5G:UL:CC1:RFUC:STAT OFF')  # Disable RF uplink correction
        self.VSA.write('INIT:CONT OFF')  # Disable continuous initiation
        self.VSA.query('INIT:IMM;*OPC?')  # Perform initial sweep
        print('VSA configuration complete.')
        logger.info("Performed pre-sweep in VSA_Config")

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
        time.sleep(0.1)  # Stabilize frequency

    @method_timer
    def VSA_sweep(self):
        """Perform VSA sweep for measurement."""
        logger.info("Performing VSA sweep")
        self.VSA.write('INIT:CONT OFF')  # Disable continuous sweep
        self.VSA.query('INIT:IMM;*OPC?')  # Initiate sweep and wait

    @method_timer
    def VSA_get_info(self):
        """Get and return VSA configuration info."""
        config = f"{self.freq / 1e9:.3f}GHz_{self.bw}MHz_{self.dupl}_{self.ldir}_{self.scs}_{self.rb}RB_{self.rbo}RBO_{self.mod}"
        logger.info(f"VSA configuration: {config}")
        return config

    @method_timer
    def VSA_level(self):
        """Adjust VSA input level."""
        logger.info("Adjusting VSA input level")
        self.VSA.query(':SENS:ADJ:LEV;*OPC?')

    @method_timer
    def VSA_get_EVM(self):
        """Measure and return EVM (Error Vector Magnitude).

        Returns:
            float: EVM value in dB.
        """
        logger.info("Measuring EVM")
        try:
            self.VSA.write(
                f':CONF:NR5G:MEAS EVM;:SENS:SWE:TIME {self.swp_time};:SENS:NR5G:FRAM:COUN 1;:SENS:NR5G:FRAM:SLOT 1;*OPC')
            self.VSA.write('INIT:CONT OFF')  # Disable continuous sweep
            self.VSA.query('INIT:IMM;*OPC?')  # Pre-sweep
            self.VSA.query('INIT:IMM;*OPC?')  # Measurement sweep
            evm = self.VSA.queryFloat(':FETC:CC1:SUMM:EVM:ALL:AVER?')  # Fetch EVM
            logger.info(f"EVM measured: {evm:.2f} dB")
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
        try:
            self.VSA.write(':CONF:NR5G:MEAS ACLR;*OPC')  # Configure ACLR measurement
            self.VSA.write(f':SENS:FREQ:CENT {self.freq};:SENS:POW:ACH:ACP 2;*OPC')  # Set frequency and pairs
            self.VSA.write('INIT:CONT OFF')  # Disable continuous sweep
            self.VSA.query('INIT:IMM;*OPC?')  # Pre-sweep
            self.VSA.query('INIT:IMM;*OPC?')  # Measurement sweep
            aclr = self.VSA.query(':CALC:MARK:FUNC:POW:RES? ACP')  # Fetch ACLR
            logger.info(f"ACLR measured: {aclr}")
            self.VSA.write(':CONF:NR5G:MEAS EVM;*OPC')  # Revert to EVM measurement
            return str(aclr).strip()
        except Exception as e:
            logger.error(f"ACLR measurement failed: {e}")
            return ''

    def VSA_get_chPwr(self):
        """Measure and return channel power.

        Returns:
            float: Channel power in dBm.
        """
        logger.info("Measuring channel power")
        try:
            ch_pwr = self.VSA.queryFloat(':CALC:NR5G:CHP?')  # Fetch channel power
            logger.info(f"Channel power measured: {ch_pwr:.2f} dBm")
            return ch_pwr
        except Exception as e:
            logger.error(f"Channel power measurement failed: {e}")
            return float('nan')