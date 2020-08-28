#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Generic classes, methods, functions used for more than one reanalysis.
#
#
# (C) Copyright Stephan Gruber (2017)
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#===============================================================================
from __future__  import print_function

from datetime    import datetime, timedelta
from os          import mkdir, path, makedirs, listdir
from fnmatch     import filter as fnmatch_filter

import pandas  as pd
import netCDF4 as nc
import numpy as np

import glob

import re

# handle python 3 string types
try:
    basestring
except NameError:
    basestring = str

try:
    import ESMF

    # Check ESMF version.  7.0.1 behaves differently than 7.1.0r
    ESMFv = int(re.sub("[^0-9]", "", ESMF.__version__))
    ESMFnew = ESMFv > 701
except ImportError:
    print("*** ESMF not imported, interpolation not possible. ***")
    pass


class ParameterIO(object):
    """
    Reads generic parameter files and makes values available as dictionary.

    # read file
    par = ParameterIO('examples/par/examples.globsim_download')

    # access first reanalysis variable
    par.variables[0]

    # access data_directory
    par.data_directory

    # access north end of bounding box
    par.bbN
    """

    def __init__(self, pfile):
        """
        Instantiate a new object and set conventions.
        """
        self.fmt_date = "%Y/%m/%d"
        self.pfile    = pfile
        self.comment  = "#"
        self.assign   = "="
        self.file_read()

    def __getitem__(self, item):
        attr = getattr(self, item)
        return(attr)

    def file_read(self):
        """
        Read parameter file into a list of strings (each line is one entry) and
        parse content into a dictionary.
        """
        # read file
        with open(self.pfile, "r") as myfile:
            inpts_str = myfile.readlines()

        # parse content
        for line in inpts_str:
            d = self.line2dict(line)
            if d is not None:
                self.__dict__[list(d.keys())[0]] = list(d.values())[0]

    def __is_only_comment(self, lin):
        # checks whether line contains nothing but comment
        for c in lin:
            if c != " ":
                if c == self.comment:
                    return True
                else:
                    return False

    def __string2datetime(self, valu):
        # checks if value is a date string. If true, a datetime object is
        # returned. If false, value is returned unchanged.
        if not isinstance(valu, basestring):
            return valu

        # see if time conversion is possible
        try:
            valu = datetime.strptime(valu, self.fmt_date)
        except ValueError:
            pass
        return valu

    def __string2logical(self, valu):
        # checks if value is a true / false. If true, a logical object is
        # returned. If false, value is returned unchanged.
        if not isinstance(valu, basestring):
            return valu

        # see if time conversion is possible
        if valu.lower() == "false":
            valu = False
        if valu.lower() == "true":
            valu = True
        return valu

    def __string2datetime_list(self, dates):
        # convert list of date strings to datetime
        return [self.__string2datetime(date) for date in dates]

    def line2dict(self, lin):
        """
        Converts one line of a parameter file into a dictionary. Comments
        are recognised and ignored, float vectors are preserved, datetime
        converted from string.
        """
        # Check if this is valid
        if self.__is_only_comment(lin):
            return None

        # Remove possible trailing comment form line
        lin = lin.split(self.comment)[0]

        # Discard lines without value assignment
        if len(lin.split(self.assign)) != 2:
            return None

        # Extract name and value, strip of leading/trailling blanks
        name = lin.split(self.assign)[0].strip()
        valu = lin.split(self.assign)[1].strip()

        # Make a vector is commas are found
        if valu.find(",") > 0:
            # Convert to float or list of float if numeric
            try:
                valu = list(map(float, valu.split(",")))
            except ValueError:
                valu = list(valu.split(","))
                valu = [v.strip() for v in valu]
        else:
            try:
                valu = float(valu)
            except ValueError:
                pass

        # Convert to datetime if it is datetime
        valu = self.__string2datetime(valu)

        # Convert to logical if logical
        valu = self.__string2logical(valu)

        # Make dictionary and return
        return {name: valu}


class GenericDownload(object):
    """
    Generic functionality for download classes
    """

    def __init__(self, pfile):
        # read parameter file
        self.pfile = pfile
        self.par = par = ParameterIO(self.pfile)

        self._set_elevation(par)
        self._set_area(par)
        self._check_area(par)

        self.variables = par.variables

    def _check_area(self, par):
        if (par.bbN < par.bbS) or (par.bbE < par.bbW):
            raise ValueError("Bounding box is invalid: {}".format(self.area))

        if (np.abs(par.bbN - par.bbS) < 1.5) or (np.abs(par.bbE - par.bbW) < 1.5):
            raise ValueError("Download area is too small to conduct interpolation.")

    def _set_area(self, par):
        self.area  = {'north': par.bbN,
                      'south': par.bbS,
                      'west' : par.bbW,
                      'east' : par.bbE}

    def _set_elevation(self, par):
        self.elevation = {'min' : par.ele_min,
                          'max' : par.ele_max}

    def _set_data_directory(self, name):
        self.directory = path.join(self.par.project_directory, name)
        if not path.isdir(self.directory):
            makedirs(self.directory)


class GenericInterpolate:

    def __init__(self, ifile):
        # read parameter file
        self.ifile = ifile
        self.par = par = ParameterIO(self.ifile)
        self.dir_out = self.make_output_directory(par)
        self.variables = par.variables
        self.list_name = par.station_list.split(path.extsep)[0]
        self.stations_csv = path.join(par.project_directory,
                                      'par', par.station_list)

        # read station points
        self.stations = StationListRead(self.stations_csv)

        # time bounds, add one day to par.end to include entire last day
        self.date  = {'beg' : par.beg,
                      'end' : par.end + timedelta(days=1)}

        # chunk size: how many time steps to interpolate at the same time?
        # A small chunk size keeps memory usage down but is slow.
        self.cs  = int(par.chunk_size)

    def TranslateCF2short(self, dpar):
        """
        Map CF Standard Names into short codes used in netCDF files.
        """
        varlist = []
        for var in self.variables:
            varlist.append(dpar.get(var))
        # drop none
        varlist = [item for item in varlist if item is not None]
        # flatten
        varlist = [item for sublist in varlist for item in sublist]
        return(varlist)

    def interp2D(self, ncfile_in, ncf_in, points, tmask_chunk,
                        variables=None, date=None):
        """
        Bilinear interpolation from fields on regular grid (latitude, longitude)
        to individual point stations (latitude, longitude). This works for
        surface and for pressure level files

        Args:
            ncfile_in: Full path to an Era-Interim derived netCDF file. This can
                       contain wildcards to point to multiple files if temporal
                       chunking was used.

            ncf_in: A netCDF4.MFDataset derived from reading in Era-Interim
                    multiple files (def ERA2station())

            points: A dictionary of locations. See method StationListRead in
                    generic.py for more details.

            tmask_chunk:

            variables:  List of variable(s) to interpolate such as
                        ['r', 't', 'u','v', 't2m', 'u10', 'v10', 'ssrd', 'strd', 'tp'].
                        Defaults to using all variables available.

            date: Directory to specify begin and end time for the derived time
                  series. Defaluts to using all times available in ncfile_in.

        Example:
            from datetime import datetime
            date  = {'beg' : datetime(2008, 1, 1),
                      'end' : datetime(2008,12,31)}
            variables  = ['t','u', 'v']
            stations = StationListRead("points.csv")
            ERA2station('era_sa.nc', 'era_sa_inter.nc', stations,
                        variables=variables, date=date)
        """

        # is it a file with pressure levels?
        pl = 'level' in ncf_in.dimensions.keys()

        # get spatial dimensions
        if pl: # only for pressure level files
            lev  = ncf_in.variables['level'][:]
            nlev = len(lev)

        # test if time steps to interpolate remain
        nt = sum(tmask_chunk)
        if nt == 0:
            raise ValueError('No time steps from netCDF file selected.')

        # get variables
        varlist = [str_encode(x) for x in ncf_in.variables.keys()]
        self.remove_select_variables(varlist, pl)

        # list variables that should be interpolated
        if variables is None:
            variables = varlist
        # test is variables given are available in file
        if (set(variables) < set(varlist) == 0):
            raise ValueError('One or more variables not in netCDF file.')

        sgrid = self.create_source_grid(ncfile_in)

        # create source field on source grid
        if pl:  # only for pressure level files
            sfield = ESMF.Field(sgrid, name='sgrid',
                                staggerloc=ESMF.StaggerLoc.CENTER,
                                ndbounds=[len(variables), nt, nlev])
        else: # 2D files
            sfield = ESMF.Field(sgrid, name='sgrid',
                                staggerloc=ESMF.StaggerLoc.CENTER,
                                ndbounds=[len(variables), nt])

        self.nc_data_to_source_field(variables, sfield, ncf_in, tmask_chunk, pl)

        locstream = self.create_loc_stream()

        # create destination field
        if pl: # only for pressure level files
            dfield = ESMF.Field(locstream, name='dfield',
                                ndbounds=[len(variables), nt, nlev])
        else:
            dfield = ESMF.Field(locstream, name='dfield',
                                ndbounds=[len(variables), nt])

        dfield = self.regrid(sfield, dfield)

        return dfield, variables

    def make_output_directory(self, par):
        """make directory to hold outputs"""

        dirIntp = path.join(par.project_directory, 'interpolated')

        if not (path.isdir(dirIntp)):
            makedirs(dirIntp)

        return dirIntp

    def create_source_grid(self, ncfile_in):
        # Create source grid from a SCRIP formatted file. As ESMF needs one
        # file rather than an MFDataset, give first file in directory.
        flist = np.sort(fnmatch_filter(listdir(self.dir_inp), path.basename(ncfile_in)))
        ncsingle = path.join(self.dir_inp, flist[0])
        sgrid = ESMF.Grid(filename=ncsingle, filetype=ESMF.FileFormat.GRIDSPEC)

        return sgrid

    def create_loc_stream(self):
        # CANNOT have third dimension!!!
        locstream = ESMF.LocStream(len(self.stations),
                                   coord_sys=ESMF.CoordSys.SPH_DEG)
        locstream["ESMF:Lon"] = list(self.stations['longitude_dd'])
        locstream["ESMF:Lat"] = list(self.stations['latitude_dd'])

        return locstream

    @staticmethod
    def regrid(sfield, dfield):
    # regridding function, consider ESMF.UnmappedAction.ERROR
        regrid2D = ESMF.Regrid(sfield, dfield,
                                regrid_method=ESMF.RegridMethod.BILINEAR,
                                unmapped_action=ESMF.UnmappedAction.IGNORE,
                                dst_mask_values=None)

        # regrid operation, create destination field (variables, times, points)
        dfield = regrid2D(sfield, dfield)
        sfield.destroy()  # free memory

        return dfield

    @staticmethod
    def nc_data_to_source_field(variables, sfield, ncf_in, tmask_chunk, pl):
        # assign data from ncdf: (variable, time, latitude, longitude)
        for n, var in enumerate(variables):

            if pl:  # only for pressure level files
                if ESMFnew:
                    sfield.data[:,:,n,:,:] = ncf_in.variables[var][tmask_chunk,:,:,:].transpose((3, 2, 0, 1))
                else:
                    sfield.data[n,:,:,:,:] = ncf_in.variables[var][tmask_chunk,:,:,:].transpose((0, 1, 3, 2))

            else:
                if ESMFnew:
                    sfield.data[:,:,n,:] = ncf_in.variables[var][tmask_chunk,:,:].transpose((2, 1, 0))
                else:
                    sfield.data[n,:,:,:] = ncf_in.variables[var][tmask_chunk,:,:].transpose((0, 2, 1))

    @staticmethod
    def remove_select_variables(varlist, pl):
        varlist.remove('time')
        varlist.remove('latitude')
        varlist.remove('longitude')
        if pl: # only for pressure level files
            varlist.remove('level')

    @staticmethod
    def calculate_weights(elev_diff, va, vb):
        wa = np.absolute(elev_diff.ravel()[vb])
        wb = np.absolute(elev_diff.ravel()[va])
        wt = wa + wb
        wa /= wt # Apply after ravel() of data.
        wb /= wt # Apply after ravel() of data.

        return wa, wb


class GenericScale:

    def __init__(self, sfile):
        # read parameter file
        self.sfile = sfile
        self.par = par = ParameterIO(self.sfile)
        self.intpdir = path.join(par.project_directory, 'interpolated')
        self.scdir = self.makeOutDir(par)
        self.list_name = par.station_list.split(path.extsep)[0]

        # get the station file
        self.stations_csv = path.join(par.project_directory,
                                      'par', par.station_list)
        # read station points
        self.stations = StationListRead(self.stations_csv)

        # read kernels
        self.kernels = par.kernels
        if not isinstance(self.kernels, list):
            self.kernels = [self.kernels]

    def getOutNCF(self, par, src, scaleDir='scale'):
        """make out file name"""

        timestep = str(par.time_step) + 'h'
        src = '_'.join(['scaled', src, timestep])
        src = src + '.nc'
        fname = path.join(self.scdir, src)

        return fname

    def makeOutDir(self, par):
        """make directory to hold outputs"""

        dirSC = path.join(par.project_directory, 'scaled')

        if not (path.isdir(dirSC)):
            makedirs(dirSC)

        return dirSC


def variables_skip(variable_name):
    """
    Which variable names to use? Drop the ones that are dimensions.
    """
    skip = 0
    dims = ('time', 'level', 'latitude', 'longitude', 'station', 'height')
    if variable_name in dims:
        skip = 1
    return skip

def StationListRead(sfile):
    """
    Reads ASCII station list and returns a pandas dataframe.

    # read station list
    stations = StationListRead('examples/par/examples_list1.globsim_interpolate')
    print(stations['station_number'])
    """
    # read file
    raw = pd.read_csv(sfile)
    raw = raw.rename(columns=lambda x: x.strip())
    return(raw)


def convert_cummulative(data):
    """
    Convert values that are serially cummulative, such as precipitation or
    radiation, into a cummulative series from start to finish that can be
    interpolated on for sacling.
    data: 1-dimensional time series
    """
    # get increment per time step
    diff = np.diff(data)
    diff = np.concatenate(([data[0]], diff))

    # where new forecast starts, the increment will be smaller than 0
    # and the actual value is used
    mask = diff < 0
    diff[mask] = data[mask]

    # get full cummulative sum
    return np.cumsum(diff, dtype=np.float64)

def cummulative2total(data, time):
    """
    Convert values that are serially cummulative, such as precipitation or
    radiation, into a cummulative series from start to finish that can be
    interpolated on for sacling.
    data: 1-dimensional time series
    """
    # get increment per time step
    diff = np.diff(data)
    diff = np.concatenate(([data[0]], diff))

    # where new forecast starts, the increment will be smaller than 0
    # and the actual value is used

    mask = [timei.hour in [3, 15] for timei in time]
    diff[mask] = data[mask]

    mask = diff < 0
    diff[mask] = 0

    return diff

def get_begin_date(par, data_folder, match_strings):
    """ Get the date to begin downloading when some files already exist
    
    Parameters
    ----------
    par : ParameterIO object
    data_folder : str
        name of subdirectory containing data files. Examples: merra2, era5
    match_strings : list
        list of glob-style strings to check. Examples ["merra_pl*", "merra_sa*","merra_sf*"]
    Returns
    -------
    datetime
        datetime object corresponding to the desired begin date (replaces par['beg'])
    This makes an inventory of all the files that have been downloaded so far and
    returns the next date to begin downloading.  If all match_strings are downloaded up to the same
    day, then the following day is returned. Otherwise, the 
    """
    directory = par['project_directory']
    print("Searching for existing files in directory")
    if not all([len(glob.glob(path.join(directory, data_folder, s))) > 0 for s in match_strings]):
        print("No existing files found. Starting download from {}".format(par['beg'].strftime("%Y-%m-%d")))
        return par['beg']

    datasets = [nc.MFDataset(path.join(directory, data_folder, s)) for s in match_strings]
    dates = [nc.num2date(x['time'][:], x['time'].units, x['time'].calendar) for x in datasets]

    latest = [max(d) for d in dates]
    latest = [dt.replace(hour=0, minute=0, second=0, microsecond=0) for dt in latest]
    latest_complete = min(latest)

    begin_date = latest_complete + timedelta(days=1)

    print("Found some files in directory. Beginning download on {}".format(begin_date.strftime("%Y-%m-%d"))    )
    return(begin_date)
def series_interpolate(time_out, time_in, value_in, cum=False):
    """
    Interpolate single time series. Convenience function for usage in scaling
    kernels.
    time_out: Array of times [s] for which output is desired. Integer.
    time_in:  Array of times [s] for which value_in is given. Integer.
    value_in: Value time series. Must have same length as time_in.
    cum:      Is valiable serially cummulative like LWin? Default: False.
    """
    time_step_sec = time_out[1]-time_out[0]

    # convert to continuous cummulative, if values are serially cummulative
    if cum:
        value_in = convert_cummulative(value_in)

    # interpolate
    vi = np.interp(time_out, time_in, value_in)

    # convert from cummulative to normal time series if needed
    if cum:
        vi = np.diff(vi) / time_step_sec
        vi = np.float32(np.concatenate(([vi[0]], vi)))

    return vi

def str_encode(value, encoding = "UTF8"):
    """
    handles encoding to allow compatibility between python 2 and 3
    specifically with regards to netCDF variables.   Python 2 imports
    variable names as unicode, whereas python 3 imports them as str.
    """
    if type(value) == str:
        return(value)
    else:
        return(value.encode(encoding))

def create_globsim_directory(target_dir, name):
    """
    creates globsim directory
    """
    # create top-level
    TL = path.join(target_dir, name)
    mkdir(TL)

    # create subdirectories
    mkdir(path.join(TL, "eraint"))
    mkdir(path.join(TL, "Grib"))
    mkdir(path.join(TL, "jra55"))
    mkdir(path.join(TL, "merra2"))
    mkdir(path.join(TL, "par"))
    mkdir(path.join(TL, "scale"))
    mkdir(path.join(TL, "station"))
    mkdir(path.join(TL, "era5"))

    return(True)


def get_begin_date(par, data_folder, match_strings):
    """ Get the date to begin downloading when some files already exist
    
    Parameters
    ----------
    par : ParameterIO object
    data_folder : str
        name of subdirectory containing data files. Examples: merra2, era5
    match_strings : list
        list of glob-style strings to check. Examples ["merra_pl*", "merra_sa*","merra_sf*"]
    
    Returns
    -------
    datetime
        datetime object corresponding to the desired begin date (replaces par['beg'])
        
    This makes an inventory of all the files that have been downloaded so far and
    returns the next date to begin downloading.  If all match_strings are downloaded up to the same
    day, then the following day is returned. Otherwise, the 
    """
    directory = par['project_directory']
    print("Searching for existing files in directory")
    
    if not all([len(glob.glob(path.join(directory, data_folder, s))) > 0 for s in match_strings]):
        print("No existing files found. Starting download from {}".format(par['beg'].strftime("%Y-%m-%d")))
        return par['beg']
        
    datasets = [nc.MFDataset(path.join(directory, data_folder, s)) for s in match_strings]
    dates = [nc.num2date(x['time'][:], x['time'].units, x['time'].calendar) for x in datasets]
    
    latest = [max(d) for d in dates]
    latest = [dt.replace(hour=0, minute=0, second=0, microsecond=0) for dt in latest]
    latest_complete = min(latest)

    begin_date = latest_complete + timedelta(days=1)
    
    print("Found some files in directory. Beginning download on {}".format(begin_date.strftime("%Y-%m-%d"))    )
    return(begin_date)