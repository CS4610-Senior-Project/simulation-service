#-*- coding: iso-8859-1 -*-
#------------------------------------------------------------
# Generated by Simcenter Amesim 2310.
# From "C:/Users/PhotonUser/My Files/OneDrive/Files/simulation_service/examples/plane.ame" system,
# Created: 11 May 2024 13:00:14
#
# Note: You can copy or modify this file without restriction.
#------------------------------------------------------------



# Initializations

# Import needed modules
import os, sys

if 'ame_apy' not in sys.modules:
   try:
      from ame_apy import *
   except ImportError:
      print('Unable to import Simcenter Amesim API module.\nCheck the AME environment variable.')

# Get license and initialize Simcenter Amesim Python API
AMEInitAPI()

# Create new "plane" system
AMECreateCircuit('plane')

# Add components of 'top circuit'

# Add "aero_fd_6dof_thrust" component
AMEAddComponent('aero_fd_6dof_thrust', 'aero_fd_6dof_thrust', (241, 156))

# Set "ATBFD6DOFTHR0000" submodel to "aero_fd_6dof_thrust" component
AMEChangeSubmodel('aero_fd_6dof_thrust', 'ATBFD6DOFTHR0000', r'$AME\libaero\submodels')

# Add "dynamic_constant_source" component
AMEAddDynamicComponent('dynamic_constant_source', 'dynamic_constant_source', '1,3', (268, 36))

# Set "SIGDYNCST01" submodel to "dynamic_constant_source" component
AMEChangeSubmodel('dynamic_constant_source', 'SIGDYNCST01', r'$AME\libsig\submodels')

# Add "aero_fd_6dof_body" component
AMEAddComponent('aero_fd_6dof_body', 'aero_fd_6dof_body', (446, 156))

# Set "ATBFD6DOFB001" submodel to "aero_fd_6dof_body" component
AMEChangeSubmodel('aero_fd_6dof_body', 'ATBFD6DOFB001', r'$AME\libaero\submodels')

# Add "dynamic_constant_source_1" component
AMEAddDynamicComponent('dynamic_constant_source', 'dynamic_constant_source_1', '2,3', (693, 240))

# Set "SIGDYNCST01" submodel to "dynamic_constant_source_1" component
AMEChangeSubmodel('dynamic_constant_source_1', 'SIGDYNCST01', r'$AME\libsig\submodels')

# Add "dynamic_constant_source_2" component
AMEAddDynamicComponent('dynamic_constant_source', 'dynamic_constant_source_2', '2,3', (489, 376))

# Set "SIGDYNCST01" submodel to "dynamic_constant_source_2" component
AMEChangeSubmodel('dynamic_constant_source_2', 'SIGDYNCST01', r'$AME\libsig\submodels')

# Add "aero_env" component
AMEAddComponent('aero_env', 'aero_env', (840, 27))

# Set "ATBENV_000" submodel to "aero_env" component
AMEChangeSubmodel('aero_env', 'ATBENV_000', r'$AME\libaero\submodels')

# Add "dynamic_time_table" component
AMEAddDynamicComponent('dynamic_time_table', 'dynamic_time_table', '1', (193, 61))

# Set "SIGUDA01" submodel to "dynamic_time_table" component
AMEChangeSubmodel('dynamic_time_table', 'SIGUDA01', r'$AME\libsig\submodels')

# Add global parameter
AMEAddGlobalParameter('time', 'time', 'ame_real_parameter', '0', '', '', '', 'null',None,0)

# Set 'aero_fd_6dof_thrust' parameters
AMESetParameterValue('MthrustRb_1@aero_fd_6dof_thrust', '0.00000000000000e+00')
AMESetParameterValue('MthrustRb_2@aero_fd_6dof_thrust', '0.00000000000000e+00')
AMESetParameterValue('MthrustRb_3@aero_fd_6dof_thrust', '0.00000000000000e+00')
AMESetParameterValue('thrust@aero_fd_6dof_thrust', '0.00000000000000e+00')
AMESetParameterValue('yawThrRb@aero_fd_6dof_thrust', '0.00000000000000e+00')
AMESetParameterValue('pitchThrRb@aero_fd_6dof_thrust', '0.00000000000000e+00')
AMESetParameterValue('maxThrust@aero_fd_6dof_thrust', '1.50000000000000e+05')
AMESetParameterValue('tc@aero_fd_6dof_thrust', '1.00000000000000e+00')
AMESetParameterValue('sigmin@aero_fd_6dof_thrust', '0.00000000000000e+00')
AMESetParameterValue('sigmax@aero_fd_6dof_thrust', '1.00000000000000e+00')
AMESetParameterValue('envindex@aero_fd_6dof_thrust', '1')

# Set 'dynamic_constant_source' parameters
AMESetParameterValue('k@dynamic_constant_source', '0.00000000000000e+00')
AMESetParameterValue('valDef@dynamic_constant_source', '3')
AMESetParameterValue('numOut@dynamic_constant_source', '1')
AMESetParameterValue('dimOut@dynamic_constant_source', '3')

# Set 'aero_fd_6dof_body' parameters
AMESetParameterValue('CLgRas_1@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('CLgRas_2@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('CLgRas_3@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('vGRgal_1@aero_fd_6dof_body', '1.00000000000000e+30')
AMESetParameterValue('vGRgal_2@aero_fd_6dof_body', '1.00000000000000e+30')
AMESetParameterValue('vGRgal_3@aero_fd_6dof_body', '1.00000000000000e+30')
AMESetParameterValue('OrGRgal_1@aero_fd_6dof_body', '1.00000000000000e+30')
AMESetParameterValue('OrGRgal_2@aero_fd_6dof_body', '1.00000000000000e+30')
AMESetParameterValue('OrGRgal_3@aero_fd_6dof_body', '1.00000000000000e+30')
AMESetParameterValue('CGRas_1@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('CGRas_2@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('CGRas_3@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('P2bodyIndex@aero_fd_6dof_body', '1.00000000000000e+00')
AMESetParameterValue('CCtRas_1@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('CCtRas_2@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('CCtRas_3@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('absangrateRb_1@aero_fd_6dof_body', '1.00000000000000e+30')
AMESetParameterValue('absangrateRb_2@aero_fd_6dof_body', '1.00000000000000e+30')
AMESetParameterValue('absangrateRb_3@aero_fd_6dof_body', '1.00000000000000e+30')
AMESetParameterValue('quat_1@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('quat_2@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('quat_3@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('quat_4@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('mass@aero_fd_6dof_body', '5.04000000000000e+04')
AMESetParameterValue('Ixx@aero_fd_6dof_body', '1.28000000000000e+05')
AMESetParameterValue('Iyy@aero_fd_6dof_body', '3.78100000000000e+06')
AMESetParameterValue('Izz@aero_fd_6dof_body', '4.87800000000000e+06')
AMESetParameterValue('Ixy@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('Ixz@aero_fd_6dof_body', '-1.40000000000000e+04')
AMESetParameterValue('Iyz@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('veGxbinit@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('veGybinit@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('veGzbinit@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('latitudeinit@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('longitudeinit@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('altitudeinit@aero_fd_6dof_body', '6.00000000000000e+03')
AMESetParameterValue('angrateXbinit@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('angrateYbinit@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('angrateZbinit@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('rollinit@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('pitchinit@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('yawinit@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('xLgas@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('yLgas@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('zLgas@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('xGas@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('yGas@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('zGas@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('xCtas@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('yCtas@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('zCtas@aero_fd_6dof_body', '0.00000000000000e+00')
AMESetParameterValue('quatPow@aero_fd_6dof_body', '8.00000000000000e-01')
AMESetParameterValue('envindex@aero_fd_6dof_body', '1')
AMESetParameterValue('quatStab@aero_fd_6dof_body', '1')

# Set 'dynamic_constant_source_1' parameters
AMESetParameterValue('k@dynamic_constant_source_1', '0.00000000000000e+00')
AMESetParameterValue('valDef@dynamic_constant_source_1', '3')
AMESetParameterValue('numOut@dynamic_constant_source_1', '2')
AMESetParameterValue('dimOut@dynamic_constant_source_1', '3')

# Set 'dynamic_constant_source_2' parameters
AMESetParameterValue('k@dynamic_constant_source_2', '0.00000000000000e+00')
AMESetParameterValue('valDef@dynamic_constant_source_2', '3')
AMESetParameterValue('numOut@dynamic_constant_source_2', '2')
AMESetParameterValue('dimOut@dynamic_constant_source_2', '3')

# Set 'aero_env' parameters
AMESetParameterValue('nbReg@aero_env', '1')
AMESetParameterValue('deltaISA@aero_env', '0.00000000000000e+00')
AMESetParameterValue('initUTC@aero_env', '0.00000000000000e+00')
AMESetParameterValue('planetmajor@aero_env', '6.37813700000000e+06')
AMESetParameterValue('planetminor@aero_env', '6.35675231425000e+06')
AMESetParameterValue('planetflat@aero_env', '2.98257223563000e+02')
AMESetParameterValue('planetspeed@aero_env', '7.29211501000000e-05')
AMESetParameterValue('gravitysl@aero_env', '9.80616000000000e+00')
AMESetParameterValue('timezone@aero_env', '0.00000000000000e+00')
AMESetParameterValue('yp@aero_env', '0.00000000000000e+00')
AMESetParameterValue('xp@aero_env', '0.00000000000000e+00')
AMESetParameterValue('gamma@aero_env', '1.29410000000000e+00')
AMESetParameterValue('rspe@aero_env', '1.88918000000000e+02')
AMESetParameterValue('SAPSL@aero_env', '6.99000000000000e-03')
AMESetParameterValue('SATSL@aero_env', '2.42150000000000e+02')
AMESetParameterValue('SADSL@aero_env', '1.52798600000000e-02')
AMESetParameterValue('altmax@aero_env', '7.00000000000000e+03')
AMESetParameterValue('SAT0@aero_env', '2.73000000000000e+02')
AMESetParameterValue('beta@aero_env', '1.45800000000000e-06')
AMESetParameterValue('S@aero_env', '2.22000000000000e+02')
AMESetParameterValue('mu0@aero_env', '1.37000000000000e-05')
AMESetParameterValue('envindex@aero_env', '1')
AMESetParameterValue('atmmodel@aero_env', '1')
AMESetParameterValue('gravitymodel@aero_env', '1')
AMESetParameterValue('planetframe@aero_env', '1')
AMESetParameterValue('axisPerturbation@aero_env', '1')
AMESetParameterValue('planetgeom@aero_env', '1')
AMESetParameterValue('spheroidparam@aero_env', '1')
AMESetParameterValue('userstarttime@aero_env', '2')
AMESetParameterValue('daysavingtime@aero_env', '0')
AMESetParameterValue('startyear@aero_env', '1970')
AMESetParameterValue('startmonth@aero_env', '1')
AMESetParameterValue('startday@aero_env', '1')
AMESetParameterValue('starthour@aero_env', '0')
AMESetParameterValue('startminute@aero_env', '0')
AMESetParameterValue('startsecond@aero_env', '0')
AMESetParameterValue('dayType@aero_env', '1')
AMESetParameterValue('model@aero_env', '1')
AMESetParameterValue('extParamProf@aero_env', '1')
AMESetParameterValue('extParamEnv@aero_env', '1')
AMESetParameterValue('freqEnv@aero_env', '1')
AMESetParameterValue('freqProf@aero_env', '1')
AMESetParameterValue('altExtVal@aero_env', '1')
AMESetParameterValue('viscType@aero_env', '2')
AMESetParameterValue('ExprFileSAP@aero_env', '1e3*0.699*exp(-0.00009*alt)')
AMESetParameterValue('ExprFileSAT@aero_env', '(-31-0.000998*alt)+273.15')
AMESetParameterValue('ExprFileLambda@aero_env', '1.0e-4')
AMESetParameterValue('ExprFileMu@aero_env', '1.37e-5')

# Set 'dynamic_time_table' parameters
AMESetParameterValue('xminslope@dynamic_time_table', '0.00000000000000e+00')
AMESetParameterValue('xmaxslope@dynamic_time_table', '0.00000000000000e+00')
AMESetParameterValue('spline@dynamic_time_table', '1')
AMESetParameterValue('lmode@dynamic_time_table', '1')
AMESetParameterValue('disc@dynamic_time_table', '2')
AMESetParameterValue('bcond@dynamic_time_table', '1')
AMESetParameterValue('cmode@dynamic_time_table', '1')
AMESetParameterValue('outputtype@dynamic_time_table', '1')
AMESetParameterValue('ucol@dynamic_time_table', '2')
AMESetParameterValue('smode@dynamic_time_table', '1')
AMESetParameterValue('initMethod@dynamic_time_table', '1')
AMESetParameterValue('tcol@dynamic_time_table', '1')
AMESetParameterValue('filename@dynamic_time_table', 'testtable.txt')
AMESetParameterValue('numOutputs@dynamic_time_table', '1')

# Establish connections inside 'top circuit'

# Connect "aero_fd_6dof_thrust" and "aero_fd_6dof_body" with a line
AMEConnectTwoPortsWithLine('aero_fd_6dof_body', 2, 'aero_fd_6dof_thrust', 0, 'linear', ())

# Connect "aero_fd_6dof_thrust" and "dynamic_constant_source" with a line
AMEConnectTwoPortsWithLine('dynamic_constant_source', 0, 'aero_fd_6dof_thrust', 1, 'control_1', ((312, 50)))

# Connect "aero_fd_6dof_thrust" and "dynamic_time_table" with a line
AMEConnectTwoPortsWithLine('aero_fd_6dof_thrust', 2, 'dynamic_time_table', 0, 'control', ((249, 75)))

# Connect "aero_fd_6dof_body" and "dynamic_constant_source_2" with a line
AMEConnectTwoPortsWithLine('dynamic_constant_source_2', 0, 'aero_fd_6dof_body', 0, 'control_3', ((587, 390)))

# Connect "aero_fd_6dof_body" and "dynamic_constant_source_1" with a line
AMEConnectTwoPortsWithLine('dynamic_constant_source_1', 0, 'aero_fd_6dof_body', 1, 'control_2', ((754, 254), (754, 209)))

# Set run parameters

# Generate code
AMEGenerateCode()

# Add 'Save next' and 'Lock State' flags

# Add text items

# Save 'plane.ame' system
AMECloseCircuit(True)

# Finalize script

# Return license and close Simcenter Amesim Python API
AMECloseAPI(False)
