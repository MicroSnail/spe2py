#!/usr/bin/env python3
"""
spe2py imports a Princeton Instruments LightField (SPE 3.0) file into a python environment.
"""

import numpy as np
import tkinter as tk
import untangle
from tkinter import filedialog as fdialog


def get_file():
    root = tk.Tk()
    root.withdraw()
    fname = fdialog.askopenfilename()
    return fname


def read_header(filename):
    f = open(filename, 'rb')
    header = np.fromfile(f, np.uint8, 4100)
    f.close()
    return header


def read_footer(filename):
    f = open(filename, 'rb')
    f.seek(678)
    footer_pos = np.fromfile(f, np.uint64, 8)[0]
    f.seek(footer_pos)

    xmlfile = open('xmlFile.tmp', 'w')
    xmltext = f.read().decode('utf-8')

    xmlfile.write(xmltext)

    loaded_footer = untangle.parse('xmlFile.tmp')

    f.close()
    return loaded_footer

    # TODO: print entire footer structure


def get_specs(header, footer):
    cameraSettings = footer.SpeFormat.DataHistories.DataHistory.Origin.Experiment.Devices.Cameras.Camera
    regionOfInterest = cameraSettings.ReadoutControl.RegionsOfInterest.CustomRegions.RegionOfInterest

    if isinstance(regionOfInterest, list):
        nRoI = len(regionOfInterest)
        RoI = regionOfInterest
    else:
        nRoI = 1
        RoI = np.array([regionOfInterest])

    wavelength = footer.SpeFormat.Calibrations.WavelengthMapping.Wavelength.cdata

    nframes = header[1446:1447].astype(np.uint16)[0]
    dtype_code = header[108:109].astype(np.uint16)[0]

    if dtype_code == 0:
        dtype = np.float32
    elif dtype_code == 1:
        dtype = np.int32
    elif dtype_code == 2:
        dtype = np.int16
    elif dtype_code == 3:
        dtype = np.uint16
    elif dtype_code == 8:
        dtype = np.uint32

    return RoI, wavelength, nRoI, nframes, dtype


def get_coords(header, RoI, nRoI):
    xcoord = [[] for x in range(0, nRoI)]
    ycoord = [[] for x in range(0, nRoI)]

    for roi_ind in range(0, nRoI):
        working_RoI = RoI[roi_ind]
        ystart = int(working_RoI['y'])
        ybinning = int(working_RoI['yBinning'])
        yheight = int(working_RoI['height'])
        ycoord[roi_ind] = range(ystart, (ystart + yheight), ybinning)

    # TODO: figure out wavelength rules
    for roi_ind in range(0, nRoI):
        working_RoI = RoI[roi_ind]
        xstart = int(working_RoI['x'])
        xbinning = int(working_RoI['xBinning'])
        xwidth = int(working_RoI['width'])
        xcoord[roi_ind] = range(xstart, (xstart + xwidth), xbinning)

    return xcoord, ycoord


def read_data(filename, dtype, nframes, nRoI, xcoord, ycoord):
    data = np.empty([nframes, nRoI])
    f = open(filename, 'rb')
    f.seek(4100)

    xdim = len(xcoord)
    ydim = len(ycoord)

    dataMatrix = [[0 for x in range(nRoI)] for y in range(nframes)]
    for frame in range(0, nframes):
        for RoI in range(0, nRoI):
            dataMatrix[frame][RoI] = np.fromfile(f, dtype, xdim * ydim)
            dataMatrix[frame][RoI] = np.reshape(data[frame, RoI], [ydim, xdim])
    return dataMatrix
 # TODO: fix data writing

class SPE(object):

    def __init__(self, filename, header, footer, data, xcoord, ycoord, regionsOfInterest):
        self.fid = open(filename)
        self.filename = filename
        # self.nfile = len(filename) (when mult files are done in future)
        self.header = header
        # self.footer = parse xml footer
        # self.data = read binary data
        # self.xcoord = assign xcoord from footer
        # self.ycoord = assign ycoord from footer

    def _load_size(self):
        self._xdim = np.int64(self.read_at(42, 1, np.int16)[0])
        self._ydim = np.int64(self.read_at(656, 1, np.int16)[0])

    def read_at(self, pos, size, ntype):
        self._fid.seek(pos)
        return np.fromfile(self._fid, ntype, size)

    def load_img(self):
        img = self.read_at(4100, self._xdim * self._ydim, np.uint16)
        return img.reshape((self._ydim, self._xdim))


def load():
    file = get_file()
    loaded_header = read_header(file)
    loaded_footer = read_footer(file)
    RoI, wavelength, nRoI, nframes, dtype = get_specs(loaded_header, loaded_footer)

    # loaded_spe = SPE(file, loaded_header)

    return loaded_header, loaded_footer, RoI, wavelength, nRoI, nframes, dtype


def print_footer(footer, ind=-1):
    """
    Prints the untangle footer object in tree form to easily view metadata fields. Ignores object elements that contain
    lists (e.g. ..Spectrometer.Turrets.Turret)
    :param footer: xml footer as parsed by untangle
    :param ind: counts tree arrows to print
    :return: printed footer
    """
    if dir(footer):
        ind += 1
        for item in dir(footer):
            if isinstance(getattr(footer, item), list):
                continue
            else:
                print(ind*' -->', item)
                print_footer(getattr(footer, item), ind)


