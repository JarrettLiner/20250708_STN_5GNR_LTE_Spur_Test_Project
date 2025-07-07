# File: src/measurements/spur_search.py
import logging
from src.utils.utils import method_timer
from src.instruments.bench import bench

logger = logging.getLogger(__name__)


class SpurSearch:
    """Class for FSW-K50 spur measurements."""

    def __init__(self, fundamental_ghz, rbw_mhz=0.01, spur_limit_dbm=-95, pwr=0):
        """Initialize the SpurSearch class for FSW-K50 spur measurements.

        Args:
            fundamental_ghz (float): Fundamental frequency in GHz.
            rbw_mhz (float, optional): Resolution bandwidth in MHz, default 0.01.
            spur_limit_dbm (float, optional): Spur limit in dBm, default -95.
            pwr (float, optional): VSG power in dBm, default 0.
        """
        self.fundamental_ghz = fundamental_ghz
        self.rbw_mhz = rbw_mhz
        self.spur_limit_dbm = spur_limit_dbm
        self.pwr = pwr
        self.frequency = fundamental_ghz * 1e9
        self.VSA = bench().VSA_start()  # Start VSA connection
        self.VSA.sock.settimeout(30)  # Set timeout
        self.VSG = bench().VSG_start()  # Start VSG connection
        self.VSG.sock.settimeout(30)  # Set timeout
        logger.info(f"SpurSearch initialized: fundamental={fundamental_ghz} GHz, "
                    f"RBW={rbw_mhz} MHz, spur_limit={spur_limit_dbm} dBm, VSG_power={pwr} dBm")

    @method_timer
    def VSA_config(self, fundamental_ghz=None, rbw_mhz=None, spur_limit_dbm=None):
        """Configure the FSW for spur search measurement.

        Args:
            fundamental_ghz (float, optional): Override fundamental frequency in GHz.
            rbw_mhz (float, optional): Override resolution bandwidth in MHz.
            spur_limit_dbm (float, optional): Override spur limit in dBm.
        """
        try:
            # Use provided parameters or instance defaults
            fundamental_ghz = fundamental_ghz if fundamental_ghz is not None else self.fundamental_ghz
            rbw_mhz = rbw_mhz if rbw_mhz is not None else self.rbw_mhz
            spur_limit_dbm = spur_limit_dbm if spur_limit_dbm is not None else self.spur_limit_dbm

            self.VSA.query('*RST;*OPC?')  # Reset VSA
            logger.info("FSW reset for spur search")

            #  self.VSA.write("INST:SEL 'Spectrum'")  # Select spur search application
            self.VSA.write(':INIT:SPUR')  # Disable continuous sweep
            logger.info("Selected Spurious application")

            # Define frequency ranges for spur search
            start_freq1 = (fundamental_ghz / 2) * 1e9
            stop_freq1 = fundamental_ghz * 1e9 - 1e6
            start_freq2 = fundamental_ghz * 1e9 + 1e6
            stop_freq2 = (2 * fundamental_ghz) * 1e9   #

            self.VSA.write('INIT:CONT OFF')  # Disable continuous sweep
            #  self.VSA.query('INIT:IMM;*OPC?')  # Initiate sweep and wait for completion

            # Configure Range 1 Fo/2 --> Fo-1MHz
            self.VSA.write(f"SENS:LIST:RANG1:FREQ:STAR {start_freq1:.0f}")
            self.VSA.write(f"SENS:LIST:RANG1:FREQ:STOP {stop_freq1:.0f}")
            self.VSA.write(':SENS:LIST:RANG1:FILT:TYPE NORM')  # Normal filter 3dB
            self.VSA.write(f':SENS:LIST:RANG1:BAND:RES {rbw_mhz * 1e6};*OPC')
            self.VSA.write(':SENS:LIST:RANG1:SWE:TIME:AUTO ON')  # Sweep Time Auto
            self.VSA.write('SENS:LIST:RANG1:DET RMS')  # RMS detector
            self.VSA.write('SENS:LIST:RANG1:RLEV -40')  # Reference level
            self.VSA.write('SENS:LIST:RANG1:INP:ATT:AUTO OFF')  # Auto attenuation OFF
            self.VSA.write(':SENS:LIST:RANG1:INP:ATT 0')  # Set attenuation to 0 dB
            self.VSA.write('SENS:LIST:RANG1:POIN:VAL 2001')  # Disable power noise correction
            self.VSA.write('SENS:LIST:RANG1:BRE OFF')  # Stop after sweep Off
            self.VSA.write('SENS:LIST:RANG1:POW:NCOR ON')  # Enable power noise correction
            self.VSA.write(f"SENS:LIST:RANG1:THR:STAR {spur_limit_dbm:.2f}")
            self.VSA.write(f"SENS:LIST:RANG1:THR:STOP {spur_limit_dbm:.2f}")
            self.VSA.write("SENS:LIST:RANG1:BAND:AUTO OFF")
            logger.info(f"Range 1: {start_freq1 / 1e9:.3f}–{stop_freq1 / 1e9:.3f} GHz")

            # Configure Range 2 Fo-1MHz --> Fo+1MHz
            self.VSA.write(f"SENS:LIST:RANG2:FREQ:STAR {stop_freq1:.0f}")
            self.VSA.write(f"SENS:LIST:RANG2:FREQ:STOP {start_freq2:.0f}")
            self.VSA.write(':SENS:LIST:RANG2:FILT:TYPE NORM')  # Normal filter 3dB
            self.VSA.write(f"SENS:LIST:RANG2:BAND:RES {rbw_mhz * 1e6:.0f}")
            self.VSA.write(':SENS:LIST:RANG2:SWE:TIME:AUTO ON')  # Sweep Time Auto
            self.VSA.write('SENS:LIST:RANG2:DET RMS')  # RMS detector
            self.VSA.write('SENS:LIST:RANG2:RLEV -40')  # Reference level
            self.VSA.write('SENS:LIST:RANG2:INP:ATT:AUTO OFF')  # Auto attenuation OFF
            self.VSA.write(':SENS:LIST:RANG2:INP:ATT 60')  # Set attenuation to 0 dB
            self.VSA.write('SENS:LIST:RANG2:POIN:VAL 2001')  # Disable power noise correction
            self.VSA.write('SENS:LIST:RANG2:BRE OFF')  # Stop after sweep Off
            self.VSA.write('SENS:LIST:RANG2:POW:NCOR ON')  # Enable power noise correction
            self.VSA.write(f"SENS:LIST:RANG2:THR:STAR {spur_limit_dbm:.2f}")
            self.VSA.write(f"SENS:LIST:RANG2:THR:STOP {spur_limit_dbm:.2f}")
            self.VSA.write("SENS:LIST:RANG2:BAND:AUTO OFF")
            logger.info(f"Range 2: {start_freq2 / 1e9:.3f}–{stop_freq2 / 1e9:.3f} GHz")

            # Configure Range 3 Fo+1MHz --> 2*Fo
            self.VSA.write(f"SENS:LIST:RANG3:FREQ:STAR {start_freq1:.0f}")
            self.VSA.write(f"SENS:LIST:RANG3:FREQ:STOP {stop_freq1:.0f}")
            self.VSA.write(':SENS:LIST:RANG3:FILT:TYPE NORM')  # Normal filter 3dB
            self.VSA.write(f"SENS:LIST:RANG3:FREQ:STAR {start_freq2:.0f}")
            self.VSA.write(f"SENS:LIST:RANG3:FREQ:STOP {stop_freq2:.0f}")
            self.VSA.write(f"SENS:LIST:RANG3:BAND:RES {rbw_mhz * 1e6:.0f}")
            self.VSA.write(':SENS:LIST:RANG3:SWE:TIME:AUTO ON')  # Sweep Time Auto
            self.VSA.write('SENS:LIST:RANG3:DET RMS')  # RMS detector
            self.VSA.write('SENS:LIST:RANG3:RLEV -40')  # Reference level
            self.VSA.write('SENS:LIST:RANG3:INP:ATT:AUTO OFF')  # Auto attenuation OFF
            self.VSA.write(':SENS:LIST:RANG3:INP:ATT 0')  # Set attenuation to 0 dB
            self.VSA.write('SENS:LIST:RANG3:POIN:VAL 2001')  # Disable power noise correction
            self.VSA.write('SENS:LIST:RANG3:BRE OFF')  # Stop after sweep Off
            self.VSA.write('SENS:LIST:RANG3:POW:NCOR ON')  # Enable power noise correction
            self.VSA.write(f"SENS:LIST:RANG3:THR:STAR {spur_limit_dbm:.2f}")
            self.VSA.write(f"SENS:LIST:RANG3:THR:STOP {spur_limit_dbm:.2f}")
            self.VSA.write("SENS:LIST:RANG3:BAND:AUTO OFF")
            logger.info(f"Range 3: {start_freq2 / 1e9:.3f}–{stop_freq2 / 1e9:.3f} GHz")

            #  self.VSA.query(':SENSe1:LIST:RANGe3:DELete;*OPC?')  # Delete Range 3 if it exists
            self.VSA.query(':SENS:LIST:XADJ;*OPC?')
            #  self.VSA.write(':SENS:LIST:RANG4:DEL')  # Delete Range 3 if it exists
            # self.VSA.write("LAY:ADD '1',RIGH,SDT")  # Add spur detection table (commented out)
            # self.VSA.query(':SENS:ADJ:LEV;*OPC?')  # Adjust level (commented out)
            self.VSA.query('INIT:IMM;*OPC?')  # Initiate sweep and wait for completion
            logger.info("Spur detection table configured")
        except Exception as e:
            logger.error(f"Failed to configure FSW: {e}")
            raise

    @method_timer
    def VSG_config(self, frequency_ghz=None, pwr=None):
        """Configure the VSG for spur search.

        Args:
            frequency_ghz (float, optional): Frequency in GHz.
            pwr (float, optional): Power in dBm.
        """
        try:
            frequency = (frequency_ghz * 1e9) if frequency_ghz is not None else self.frequency
            pwr = pwr if pwr is not None else self.pwr

            self.VSG.write('*RST')  # Reset VSG
            self.VSG.write(f"SOUR:FREQ:CW {frequency:.0f}")  # Set frequency
            self.VSG.write(f"SOUR:POW:LEV:IMM:AMPL {pwr:.2f}")  # Set power
            self.VSG.write("OUTP:STAT ON")  # Enable output
            logger.info(f"VSG set: frequency={frequency / 1e9:.3f} GHz, power={pwr:.2f} dBm")
        except Exception as e:
            logger.error(f"Failed to configure VSG: {e}")
            raise

    @method_timer
    def VSx_freq(self, freq):
        """Set frequency for both VSA and VSG.

        Args:
            freq (float): Frequency in Hz.
        """
        logger.info(f"Setting VSA/VSG frequency to {freq / 1e9:.3f} GHz")
        self.VSA.write(f"SENS:FREQ:CENT {freq:.0f}")
        self.VSG.write(f"SOUR:FREQ:CW {freq:.0f}")
        self.frequency = freq

    @method_timer
    def measure(self):
        """Perform the spur search measurement."""
        try:
            self.VSA.write(':INIT:CONT OFF')  # Disable continuous sweep
            self.VSA.query("INIT:IMM;*OPC?")  # Initiate sweep and wait
            logger.info("Spur search measurement completed")
        except Exception as e:
            logger.error(f"Spur search measurement failed: {e}")
            raise

    @method_timer
    def get_results(self):
        """Retrieve spur search results.

        Returns:
            list: List of tuples (frequency_hz, power_dbm) for detected spurs.
        """
        try:
            result = self.VSA.query("TRAC3:DATA? LIST")  # Fetch spur data
            spurs = []
            if result and result.strip():
                data = result.split(",")
                for i in range(0, len(data), 6):
                    try:
                        freq_hz = float(data[i])
                        power_dbm = float(data[i + 1])
                        spurs.append((freq_hz, power_dbm))
                        logger.info(f"Spur: {freq_hz / 1e9:.6f} GHz, {power_dbm:.2f} dBm")
                    except (IndexError, ValueError) as e:
                        logger.warning(f"Error parsing spur data at index {i}: {e}")
                        break
            else:
                logger.info("No spurs detected")
            return spurs
        except Exception as e:
            logger.error(f"Failed to retrieve spur results: {e}")
            return []

    def close(self):
        """Close VSA and VSG connections."""
        try:
            if self.VSA:
                self.VSA.close()
                logger.info("FSW connection closed")
            if self.VSG:
                self.VSG.write("OUTP:STAT OFF")  # Turn off VSG output
                self.VSG.close()
                logger.info("VSG connection closed")
        except Exception as e:
            logger.error(f"Error closing connections: {e}")