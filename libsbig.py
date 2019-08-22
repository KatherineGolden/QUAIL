####################################################
######### Function library for SBIG camera #########
####################################################

import ctypes
import numpy as np
from astropy.io import fits
import os

# Location of number of pictures taken, for file naming purposes
imageNumberFile = 'imageNumberFile.txt'

# If file, make one!
if not os.path.isfile(imageNumberFile):
    with open(imageNumberFile, 'w') as f:
        f.write('0\n')


# The driver
sbigd = ctypes.WinDLL('C:/Program Files (x86)/SBIG/Driver Checker 64/SBIG Drivers 3r2/DLLs/SBIGUDrv.dll')

SBIGUnivDrvCommand = sbigd.SBIGUnivDrvCommand
SBIGUnivDrvCommand.restype = ctypes.c_ushort
SBIGUnivDrvCommand.argtypes = [ctypes.c_ushort, ctypes.c_void_p, ctypes.c_void_p]

# commands
CC_OPEN_DRIVER = ctypes.c_ushort(17)
CC_CLOSE_DRIVER = ctypes.c_ushort(18)
CC_GET_DRIVER_INFO = ctypes.c_ushort(10)
CC_OPEN_DEVICE = ctypes.c_ushort(27)
CC_CLOSE_DEVICE = ctypes.c_ushort(28)
CC_GET_CCD_INFO = ctypes.c_ushort(11)
CC_ESTABLISH_LINK = ctypes.c_ushort(9)
CC_QUERY_TEMPERATURE_STATUS = ctypes.c_ushort(6)
CC_START_EXPOSURE2 = ctypes.c_ushort(50)
CC_END_EXPOSURE = ctypes.c_ushort(2)
CC_START_READOUT = ctypes.c_ushort(35)
CC_READOUT_LINE = ctypes.c_ushort(3)
CC_DUMP_LINES = ctypes.c_ushort(4)
CC_END_READOUT = ctypes.c_ushort(25)
CC_SET_TEMPERATURE_REGULATION2 = ctypes.c_ushort(51)
CC_QUERY_COMMAND_STATUS = ctypes.c_ushort(12)
CC_MISCELLANEOUS_CONTROL = ctypes.c_ushort(13)
CC_READ_OFFSET = ctypes.c_ushort(16)


class GetDriverInfoParams(ctypes.Structure):
    _fields_ = [("request", ctypes.c_ushort)]

class GetDriverInfoResults0(ctypes.Structure):
    _fields_ = [("version", ctypes.c_ushort),
                ("name", ctypes.c_char * 64),
                ("maxRequest", ctypes.c_ushort)]


def open_driver():
    return SBIGUnivDrvCommand(CC_OPEN_DRIVER, None, None)

def close_driver():
    return SBIGUnivDrvCommand(CC_CLOSE_DRIVER, None, None)

def get_driver_version():
    params = GetDriverInfoParams()
    params.request = 0  # standard info
    result = ctypes.cast(ctypes.pointer(GetDriverInfoResults0()), ctypes.c_void_p)

    ret = SBIGUnivDrvCommand(
        CC_GET_DRIVER_INFO,
        ctypes.cast(ctypes.pointer(params), ctypes.c_void_p),
        result)

    result = ctypes.cast(result, ctypes.POINTER(GetDriverInfoResults0))

    return {'version': result[0].version,
            'name': result[0].name,
            'maxRequest': result[0].maxRequest}


class ReadoutInfo(ctypes.Structure):
    _fields_ = [("mode", ctypes.c_ushort),
                ("width", ctypes.c_ushort),
                ("height", ctypes.c_ushort),
                ("gain", ctypes.c_ushort),
                ("pixelWidth", ctypes.c_ulong),
                ("pixelHeight", ctypes.c_ulong)]

class GetCCDInfoResults0(ctypes.Structure):
    _fields_ = [("firmwareVersion", ctypes.c_ushort),
                ("cameraType", ctypes.c_ushort),
                ("name", (ctypes.c_char * 64)),
                ("readoutModes", ctypes.c_ushort),
                ("readoutInfo", (ReadoutInfo * 20))]

class GetCCDInfoParams(ctypes.Structure):
    _fields_ = [("request", ctypes.c_ushort)]

class EstablishLinkParams(ctypes.Structure):
    _fields_ = [("sbigUseOnly", ctypes.c_ushort)]

class EstablishLinkResults(ctypes.Structure):
    _fields_ = [("cameraType", ctypes.c_ushort)]


def establish_link():
    params = EstablishLinkParams()
    result = ctypes.cast(ctypes.pointer(EstablishLinkResults()), ctypes.c_void_p)

    ret = SBIGUnivDrvCommand(
        CC_ESTABLISH_LINK,
        ctypes.cast(ctypes.pointer(params), ctypes.c_void_p),
        result)

    result = ctypes.cast(result, ctypes.POINTER(EstablishLinkResults))

    return

def get_ccd_info():
    params = GetCCDInfoParams()        # sends a request for information to GetCCDInfoParams()
    params.request = 0  # standard info
    result = ctypes.cast(ctypes.pointer(GetCCDInfoResults0()), ctypes.c_void_p)   # refers to results struct that contains info
    ret = SBIGUnivDrvCommand(
        CC_GET_CCD_INFO,
        ctypes.cast(ctypes.pointer(params), ctypes.c_void_p),
        result)

    if ret == 1:
        print('Camera not found!')

    result = ctypes.cast(result, ctypes.POINTER(GetCCDInfoResults0))

    return result[0].readoutInfo[0].width, result[0].readoutInfo[0].height


class OpenDeviceParams(ctypes.Structure):
    _fields_ = [('deviceType', ctypes.c_ushort),
                ('lptBaseAddress', ctypes.c_ushort),
                ('ipAddress', ctypes.c_ulong)]


def open_device():
    params = OpenDeviceParams()
    params.deviceType = 0x7F00
    ret = SBIGUnivDrvCommand(
        CC_OPEN_DEVICE,
        ctypes.cast(ctypes.pointer(params), ctypes.c_void_p),
        None)

    if ret > 0:
        print('Error opening device.')

def close_device():
    return SBIGUnivDrvCommand(CC_CLOSE_DEVICE, None, None)


class StartExposureParams2(ctypes.Structure):
    _fields_ = [("ccd", ctypes.c_ushort),
                ("exposureTime", ctypes.c_ulong),
                ("abgState", ctypes.c_ushort),
                ("openShutter", ctypes.c_ushort),
                ("readoutMode", ctypes.c_ushort),
                ("top", ctypes.c_ushort),
                ("left", ctypes.c_ushort),
                ("height", ctypes.c_ushort),
                ("width", ctypes.c_ushort)]


def start_exposure(exposureTime, height_in_pixels, width_in_pixels):
    params = StartExposureParams2()
    params.ccd = 0
    params.exposureTime = exposureTime
    params.abgState = 0
    params.openShutter = 1
    params.readoutMode = 0
    params.top = 0
    params.left = 0
    params.height = height_in_pixels
    params.width = width_in_pixels
    ret = SBIGUnivDrvCommand(
        CC_START_EXPOSURE2,
        ctypes.cast(ctypes.pointer(params), ctypes.c_void_p),
        None)

    if ret > 0:
        print('Error starting exposure.')


class EndExposureParams(ctypes.Structure):
    _fields_ = [("ccd", ctypes.c_ushort)]


def end_exposure():
    params = EndExposureParams()
    params.ccd = 0
    ret = SBIGUnivDrvCommand(
        CC_END_EXPOSURE,
        ctypes.cast(ctypes.pointer(params), ctypes.c_void_p),
        None)

    if ret > 0:
        print('Error ending exposure.')


class StartReadoutParams(ctypes.Structure):
    _fields_ = [("ccd", ctypes.c_ushort),
                ("readoutMode", ctypes.c_ushort),
                ("top", ctypes.c_ushort),
                ("left", ctypes.c_ushort),
                ("height", ctypes.c_ushort),
                ("width", ctypes.c_ushort)]


def start_readout(height_in_pixels, width_in_pixels):
    params = StartReadoutParams()
    params.ccd = 0
    params.readoutMode =0
    params.top = 0
    params.left = 0
    params.height = height_in_pixels
    params.width = width_in_pixels
    ret = SBIGUnivDrvCommand(
        CC_START_READOUT,
        ctypes.cast(ctypes.pointer(params), ctypes.c_void_p),
        None)

    if ret > 0:
        print('Error starting readout.')
        

class ReadoutLineParams(ctypes.Structure):
    _fields_ = [("ccd", ctypes.c_ushort),
                ("readoutMode", ctypes.c_ushort),
                ("pixelStart", ctypes.c_ushort),
                ("pixelLength", ctypes.c_ushort)]
    

def readout_line(pixStart, pixEnd, width_in_pixels):
    params = ReadoutLineParams()
    params.ccd = 0
    params.readoutMode = 0
    params.pixelStart = pixStart
    params.pixelLength = pixEnd
    result = ctypes.cast(ctypes.pointer(ReadoutLineParams()), ctypes.c_void_p)
    x = (ctypes.c_uint16*(width_in_pixels))()
    ret = SBIGUnivDrvCommand(
        CC_READOUT_LINE,
        ctypes.cast(ctypes.pointer(params), ctypes.c_void_p),
        x)
    
    if ret > 0:
        print('Error reading out line.')
        print("Error code:", ret)

    result = ctypes.cast(result, ctypes.POINTER(ReadoutLineParams))#.contents
    photodata = x[0:(width_in_pixels)]

    return photodata

def photoworker(photodata):
    # Saving Obtained Data
    photo_data = photodata
    photo_data = np.array(photo_data)

    # saving as a .fits:
    hdu = fits.PrimaryHDU(photo_data)
    hdul = fits.HDUList([hdu])

    imageNumber = 0
    with open(imageNumberFile, 'r') as f:
        imageNumber = int(f.readline().strip())

    hdul.writeto('CalibrationImages/pic_{n}.fits'.format(n=imageNumber))

    imageNumber += 1

    with open(imageNumberFile, 'w') as f:
        f.write(str(imageNumber) + '\n')

# Separate function for reference image so that it has a unique name
def photoworker_reference(photodata):
    # Saving Obtained Data
    photo_data = photodata
    photo_data = np.array(photo_data)

    # saving as a .fits:
    hdu = fits.PrimaryHDU(photo_data)
    hdul = fits.HDUList([hdu])

    hdul.writeto('reference_image.fits')


class DumpLinesParams(ctypes.Structure):
    _fields_ = [("ccd", ctypes.c_ushort),
                ("readoutMode", ctypes.c_ushort),
                ("lineLength", ctypes.c_ushort)]

def dump_lines():
    params = DumpLinesParams()
    params.ccd = 0
    params.readoutMode = 0
    ret = SBIGUnivDrvCommand(
        CC_DUMP_LINES,
        ctypes.cast(ctypes.pointer(params), ctypes.c_void_p),
        None)

    if ret > 0:
        print('Error dumping lines.')


class EndReadoutParams(ctypes.Structure):
    _fields_ = [("ccd", ctypes.c_ushort)]


def end_readout():
    params = EndReadoutParams()
    params.ccd = 0
    ret = SBIGUnivDrvCommand(
        CC_END_READOUT,
        ctypes.cast(ctypes.pointer(params), ctypes.c_void_p),
        None)

    if ret > 0:
        print('Error ending readout.')


class SetTemperatureRegulationParams2(ctypes.Structure):
    _fields_ = [("regulation", ctypes.c_ushort),
                ("ccdSetpoint", ctypes.c_double)]


def set_temperature(setpoint=-5):
    params = SetTemperatureRegulationParams2()
    params.regulation = 1
    params.ccdSetpoint = setpoint
    ret = SBIGUnivDrvCommand(
        CC_SET_TEMPERATURE_REGULATION2,
        ctypes.cast(ctypes.pointer(params), ctypes.c_void_p),
        None)

    if ret > 0:
        print('Error setting temperature.')


class QueryTemperatureStatusParams(ctypes.Structure):
    _fields_ = [("request", ctypes.c_ushort)]

class QueryTemperatureStatusResults2(ctypes.Structure):
    _fields_ = [("coolingEnabled", ctypes.c_ushort),  # again, unsure on the "logical" thing...
                ("fanEnabled", ctypes.c_ushort),
                ("ccdSetpoint", ctypes.c_double),
                ("imagingCCDTemperature", ctypes.c_double),
                ("trackingCCDTemperature", ctypes.c_double),
                ("externalTrackingCCDTemperature", ctypes.c_double),
                ("ambientTemperature", ctypes.c_double),
                ("imagingCCDPower", ctypes.c_double),
                ("trackingCCDPower", ctypes.c_double),
                ("externalTrackingCCDPower", ctypes.c_double),
                ("heatsinkTemperature", ctypes.c_double),
                ("fanPower", ctypes.c_double),
                ("fanSpeed", ctypes.c_double),
                ("trackingCCDSetpoint", ctypes.c_double)]


def get_temperature():
    params = QueryTemperatureStatusParams()
    params.request = 1  # standard info
    result = ctypes.cast(ctypes.pointer(QueryTemperatureStatusResults2()), ctypes.c_void_p)

    ret = SBIGUnivDrvCommand(
        CC_QUERY_TEMPERATURE_STATUS,
        ctypes.cast(ctypes.pointer(params), ctypes.c_void_p),
        result)

    result = ctypes.cast(result, ctypes.POINTER(QueryTemperatureStatusResults2))

    return result[0].imagingCCDTemperature,result[0].fanEnabled,result[0].coolingEnabled, result[0].ccdSetpoint

##    return {'CCD_temperature': result[0].imagingCCDTemperature, # CCD temp in C
##            'Fan': result[0].fanEnabled, # on(1)/off(0)
##            'Teperature_regulation': result[0].coolingEnabled, # on(1)/off(0)
##            'Setpoint': result[0].ccdSetpoint} # setpoint temp in C
    
def get_CCD_temperature():
    params = QueryTemperatureStatusParams()
    params.request = 1  # standard info
    result = ctypes.cast(ctypes.pointer(QueryTemperatureStatusResults2()), ctypes.c_void_p)

    ret = SBIGUnivDrvCommand(
        CC_QUERY_TEMPERATURE_STATUS,
        ctypes.cast(ctypes.pointer(params), ctypes.c_void_p),
        result)

    result = ctypes.cast(result, ctypes.POINTER(QueryTemperatureStatusResults2))

    return {result[0].imagingCCDTemperature} # CCD temp in C

def get_CCD_setpoint():
    params = QueryTemperatureStatusParams()
    params.request = 1  # standard info
    result = ctypes.cast(ctypes.pointer(QueryTemperatureStatusResults2()), ctypes.c_void_p)

    ret = SBIGUnivDrvCommand(
        CC_QUERY_TEMPERATURE_STATUS,
        ctypes.cast(ctypes.pointer(params), ctypes.c_void_p),
        result)

    result = ctypes.cast(result, ctypes.POINTER(QueryTemperatureStatusResults2))

    return {result[0].ccdSetpoint} # setpoint temp in C


class QueryCommandStatusParams(ctypes.Structure):
    _fields_ = [("command", ctypes.c_ushort)]

class QueryCommandStatusResults(ctypes.Structure):
    _fields_ = [("status", ctypes.c_ushort)]


def query_command_status():
    params = QueryCommandStatusParams()
    params.command = 1  # not sure what to have it equal
    result = ctypes.cast(ctypes.pointer(QueryCommandStatusResults()), ctypes.c_void_p)

    ret = SBIGUnivDrvCommand(
        CC_QUERY_COMMAND_STATUS,
        ctypes.cast(ctypes.pointer(params), ctypes.c_void_p),
        result)

    result = ctypes.cast(result, ctypes.POINTER(QueryCommandStatusResults))

    return {'Status:': result[0].status}


class MiscellaneousControlParams(ctypes.Structure):
    _fields_ = [("fanEnable", ctypes.c_ushort),
                ("shutterCommand", ctypes.c_ushort),
                ("ledState", ctypes.c_ushort)]


def misc_controls():
    params = MiscellaneousControlParams()
    params.fanEnable = True
    params.shutterCommand = 1
    params.ledState = 1
    ret = SBIGUnivDrvCommand(
        CC_MISCELLANEOUS_CONTROL,
        ctypes.cast(ctypes.pointer(params), ctypes.c_void_p),
        None)

    if ret > 0:
        print('Error with misc control.')


class ReadOffsetParams(ctypes.Structure):
    _fields_ = [("ccd", ctypes.c_ushort)]

class ReadOffsetResults(ctypes.Structure):
    _fields_ = [("offset", ctypes.c_ushort)]


def read_offset():
    params = ReadOffsetParams()
    params.ccd = 0
    result = ctypes.cast(ctypes.pointer(ReadOffsetResults()), ctypes.c_void_p)

    ret = SBIGUnivDrvCommand(
        CC_READ_OFFSET,
        ctypes.cast(ctypes.pointer(params), ctypes.c_void_p),
        result)

    result = ctypes.cast(result, ctypes.POINTER(ReadOffsetResults))

    return {'Offset:': result[0].offset}


class ReadOffsetResults2(ctypes.Structure):
    _fields_ = [("offset", ctypes.c_ushort),
                ("rms", ctypes.c_double)]


def read_offset_2():
    params = ReadOffsetParams()
    params.ccd = 0
    result = ctypes.cast(ctypes.pointer(ReadOffsetResults2()), ctypes.c_void_p)

    ret = SBIGUnivDrvCommand(
        CC_READ_OFFSET,
        ctypes.cast(ctypes.pointer(params), ctypes.c_void_p),
        result)

    result = ctypes.cast(result, ctypes.POINTER(ReadOffsetResults2))

    return {'Offset:': result[0].offset,
            'rms:': result[0].rms}

#if __name__ == '__main__':
# Can insert code here if needed
