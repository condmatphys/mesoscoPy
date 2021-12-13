# Changelog

All notable changes to mesoscoPy will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0).

## [Unreleased]
### Added
- documentation

## [0.1.1] - 2021-12-09
###Added
- conda environment installation files

### Changed
- bug corrections

## [0.1.0] - 2021-11-17
### Added
- instrument drivers: SRS_SIM928, Triton, RohdeSchwarz_SMB100A
- sweep functions include time estimate and ask user to validate
- dummy instrument: counter
- functions:
  * instrument.magnet.calibrate_magnet,
  * measurement.sweepfield, measurement.sweepfield2d
  * generate_RF_array, math.Vrf2dBm, math.dBm2Vrf
- plotting styles
- arguments TC, ampl added to init_lockin

### Changed
- renamed initialise_station -> init_station
- renamed initialise_lockin -> init_lockin
- renamed instrument.keithley -> instrument.smu, initialise_keithley -> init_smu
- moved create_instrument and add_to_station from instrument.instrument_tools to instrument.station
- moved DensityParameter, DisplacementParameter and LinearParameter from instrument.dual_gating to measurement.parameters

### Deprecated
- function measurement.array.generate_1D_sweep_array. use generate_lin_array instead

## [0.1-alpha] - 2021-09-09

### Added
- fast, 1D and 2D sweep functions
- calculate sweep time
- generate measurement arrays
- load station and add instruments to station
- parameters to make dual gate sweeps
- loading and plotting functions
- characterise contact functions
- dual gating map wrapper.
