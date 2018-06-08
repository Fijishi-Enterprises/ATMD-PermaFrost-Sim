#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
#
# Copyright Xiaojing Quan & Stephan Gruber
# =============================================================================    
# REVISION HISTORY 
# 20170510 -- Initial Version Created
# 20171208 -- First Draft Completed
#
#==============================================================================
# A scripts for downloading MERRA-2 reanalysis data:
# -- Geoppotential Height at pressure levels [time*level*lat*lon] (Unit:m) (6-hourly/day)
# -- Air Temperature at pressure levels [time*level*lat*lon] (Unit:K) (6-hourly/day)
# -- Relative Humidity at Pressure Levels[time*level*lat*lon] (Unit:1) (3-hourly/day)
# -- Easteward Wind at Pressure Levels [time*level*lat*lon] (Unit:m/s) (6-hourly/day)
# -- Northward Wind at Pressure Levels [time*level*lat*lon] (Unit:m/s) (6-hourly/day)
# -- Air Temperature at 2 Meter [time*lat*lon] (Unit:K) (1-hourly/day)
# -- Eastward Wind at 2 Meter [time*lat*lon] (Unit:K) (1-hourly/day) 
# -- Northward Wind at 2 Meter [time*lat*lon] (Unit: m/s) (1-hourly/day)
# -- Eastward Wind at 10 Meter  [time*lat*lon] (Unit: m/s) (1-hourly/day)
# -- Northward Wind at 10 Meter [time*lat*lon] (Unit: m/s) (1-hourly/day)
# -- Precipitation Flux [time*lat*lon] (Unit: kg/m2/s) (1-hourly/day)
# -- Surface Incoming Shoertwave Flux [time*lat*lon] (Unit:W/m2) (1-hourly/day)
# -- Surface Incoming Shortwave Flux Assuming Clear Sky [time*lat*lon] (Unit:W/m2) (1-hourly/day)
# -- Surface Net Downward Longwave Flux [time*lat*lon] (Unit:W/m2) (1-hourly/day)
# -- Surface Net Downward Longwave Flux Assuming Clear Sky [time*lat*lon] (Unit:W/m2) (1-hourly/day)
# -- Longwave Flux Emitted from Surface [time*lat*lon] (Unit:W/m2) (1-hourly/day)
# 
# -- Surface Absorbed Longwave Flux [time*lat*lon] (Unit:W/m2) (1-hourly/day)
# -- Surface Absorbed Longwave Flux Assuming Clear Sky [time*lat*lon] (Unit:W/m2) (1-hourly/day)
# 
# Saved as netCDF 4
#====================HOW TO RUN THIS ==========================================
#
# (1) Register a New User in Earthdata Login: 
#  https://wiki.earthdata.nasa.gov/display/EL/How+To+Register+With+Earthdata+Login
#
# (2) Authorize NASA GESDISC DATA ARCHIVE in Earthdata Login
# https://disc.gsfc.nasa.gov/registration/authorizing-gesdisc-data-access-in-earthdata_login
#
# (3) Adapt the script below with: 
#    - Authrized Username and Password (setup in .merrarc file),
#    - Input parameters: Date, Area, Elevation, Chunk_size, Variables, etc. 
#      (setup in Globsim download parameter file )
#
# (4) Obtaining the URL addresses of the objected datasets at:
#     https://disc.sci.gsfc.nasa.gov/daac-bin/FTPSubset2.pl
# 
# (5) Obtianing the mutiple datasets with spefici spacial and temporal)
#
# (6) Get all varialbes which are needed, and saved in NetCDF files 
#
#==============================================================================
# IMPORTANT Notes: 

# 1. Samples of Selected URLs list:

# url = ('https://goldsmr5.gesdisc.eosdis.nasa.gov:443/opendap/MERRA2/M2I6NPANA.5.12.4'
#        '/2016/01/MERRA2_400.inst6_3d_ana_Np.20160101.nc4')                     # 3d,6-hourly,Instantaneous,Pressure-Level, Analyzed Meteorological Fields                                                                                                                                                                                                                                                               

# url = ('https://goldsmr5.gesdisc.eosdis.nasa.gov:443/opendap/MERRA2/M2I3NPASM.5.12.4'
#        '/2016/01/MERRA2_400.inst3_3d_asm_Np.20160201.nc4')                     # 3d,3-hourly,Instantaneous,Pressure-Level,Assimilation,Assimilated Meteorological Fields 
                                                     
# url = ('https://goldsmr4.gesdisc.eosdis.nasa.gov:443/opendap/MERRA2/M2I1NXASM.5.12.4'
#         '/2016/01/MERRA2_400.inst1_2d_asm_Nx.20160102.nc4')                    # 2d,1-hourly,Instantaneous,Single-level,Assimilation,Single-Level Diagnostics,meteorological Diagnostics  

# url = ('https://goldsmr4.gesdisc.eosdis.nasa.gov:443/opendap/MERRA2/M2T1NXFLX.5.12.4'
#       '/2016/01/MERRA2_400.tavg1_2d_flx_Nx.20160101.nc4')                      # 2d,1-hourly, single-level, full horizontal resolution, Surface Flux Diagnostics

# url = ('https://goldsmr5.gesdisc.eosdis.nasa.gov:443/opendap/MERRA2/M2T3NPRAD.5.12.4'
#      '/2016/01/MERRA2_400.tavg3_3d_rad_Np.20160102.nc4')                       # 2d,1-Hourly,Time-Averaged,Single-Level,Assimilation,Radiation Diagnostics
#
# 2. Radiation Variables Processing:
# Considering the variables below as equal utilization:
#
# downwelling_shortwave_flux_in_air_assuming_clear_sky = Surface_Incoming_Shoertwave_Flux 
#
# downwelling_shortwave_flux_in_air_assuming_clear_sky = Surface_Incoming_Shortwave_Flux_Assuming_Clear_Sky
#
# downwelling_longwave_flux_in_air = Longwave Flux Emitted from Surface + Surface Net Downward Longwave Flux 
#
# downwelling_longwave_flux_in_air_assuming_clear_sky = Longwave Flux Emitted from Surface + Surface Net Downward Longwave Flux Assuming Clear Sky
            
#==============================================================================

from pydap.client      import open_url
from pydap.cas.urs     import setup_session
from datetime          import datetime, timedelta, date
from os                import path, listdir
from netCDF4           import Dataset, MFDataset
from dateutil.rrule    import rrule, DAILY
from math              import exp, floor
from generic           import ParameterIO, StationListRead, ScaledFileOpen
from generic           import series_interpolate, variables_skip, spec_hum_kgkg
from fnmatch           import filter
from scipy.interpolate import interp1d, griddata, RegularGridInterpolator, NearestNDInterpolator, LinearNDInterpolator
from time import sleep
from numpy.random import uniform
from nco import Nco

import pydap.lib
import numpy as np
import csv
import netCDF4 as nc
import math
import itertools
import pandas
import time as tc
import sys
import glob
import nco

try:
    import ESMF
except ImportError:
    print("*** ESMF not imported, interpolation not possible. ***")
    pass   

class MERRAgeneric():
    """
    Parent class for other merra classes.
    """
           
    def getURLs(self, date):                                                                                                                                          
        """ Set up urls by given range of date and type of data
            to get objected url address (2d, 3d meterological fields and radiation datasets)
            url_2dm: 2d,1-hourly,Instantaneous,Single-level,Assimilation,Single-Level Diagnostics
            url_3dm_ana: 3d,6-hourly,Instantaneous,Pressure-Level,Analyzed Meteorological Fields 
            url_3dm_asm: 3d,3-hourly,Instantaneous,Pressure-Level,Assimilation,Assimilated Meteorological Fields 
            url_2dr: 2d,1-Hourly,Time-Averaged,Single-Level,Assimilation,Radiation Diagnostics
            
            Return:
            urls_3dmana: get type of url for 3d Analyzed Meteorological Fields data
            urls_3dmasm: get type of url for 3d Assimilated Meteorological Fields data
            urls_2dm:    get type of url for 2d meterological data
            urls_2ds:    get type of url for 2d surface flux data
            urls_2dr:    get type of url fro 2d radiation diagnostics data
            
        """
        #Setup the based url strings    
        baseurl_2d = ('https://goldsmr4.gesdisc.eosdis.nasa.gov:443/opendap/MERRA2/') # baseurl for 2d dataset
        baseurl_3d = ('https://goldsmr5.gesdisc.eosdis.nasa.gov:443/opendap/MERRA2/') # baseurl for 3d dataset
        # 1980 ~ 1991 
        baseurl_3dn_1 = ('M2I6NPANA.5.12.4/','/MERRA2_100.inst6_3d_ana_Np.')            # sub url of 3d Pressure Levels Analyzed Meteorological Fields data       
        baseurl_3da_1 = ('M2I3NPASM.5.12.4/','/MERRA2_100.inst3_3d_asm_Np.')            # sub url of 3d Pressure Levels Assimilated Meteorological Fields data 
        baseurl_2dm_1 = ('M2I1NXASM.5.12.4/','/MERRA2_100.inst1_2d_asm_Nx.')            # sub url of 2d Single-Level Diagnostics     
        baseurl_2dr_1 = ('M2T1NXRAD.5.12.4/','/MERRA2_100.tavg1_2d_rad_Nx.')            # sub url of 2d radiation Diagnostics data 
        baseurl_2ds_1 = ('M2T1NXFLX.5.12.4/','/MERRA2_100.tavg1_2d_flx_Nx.')            # sub url of 2d suface flux Diagnostics data
        baseurl_2dv_1 = ('M2T1NXSLV.5.12.4/','/MERRA2_100.tavg1_2d_slv_Nx.')            # sub url of 2d 1-Hourly,Time-Averaged,Single-Level,Assimilation,Single-Level Diagnostics V5.12.4                                                                                                                                
        # 1992 ~ 2000
        baseurl_3dn_2 = ('M2I6NPANA.5.12.4/','/MERRA2_200.inst6_3d_ana_Np.')            # sub url of 3d Pressure Levels Analyzed Meteorological Fields data         
        baseurl_3da_2 = ('M2I3NPASM.5.12.4/','/MERRA2_200.inst3_3d_asm_Np.')            # sub url of 3d Pressure Levels Assimilated Meteorological Fields data 
        baseurl_2dm_2 = ('M2I1NXASM.5.12.4/','/MERRA2_200.inst1_2d_asm_Nx.')            # sub url of 2d Single-Level Diagnostics      
        baseurl_2dr_2 = ('M2T1NXRAD.5.12.4/','/MERRA2_200.tavg1_2d_rad_Nx.')            # sub url of 2d radiation Diagnostics data 
        baseurl_2ds_2 = ('M2T1NXFLX.5.12.4/','/MERRA2_200.tavg1_2d_flx_Nx.')            # sub url of 2d suface flux Diagnostics data
        baseurl_2dv_2 = ('M2T1NXSLV.5.12.4/','/MERRA2_200.tavg1_2d_slv_Nx.')            # sub url of 2d 1-Hourly,Time-Averaged,Single-Level,Assimilation,Single-Level Diagnostics V5.12.4                                                                                                                                                                                                  
        # 2001 ~ 2010  
        baseurl_3dn_3 = ('M2I6NPANA.5.12.4/','/MERRA2_300.inst6_3d_ana_Np.')            # sub url of 3d Pressure Levels Analyzed Meteorological Fields data        
        baseurl_3da_3 = ('M2I3NPASM.5.12.4/','/MERRA2_300.inst3_3d_asm_Np.')            # sub url of 3d Pressure Levels Assimilated Meteorological Fields data 
        baseurl_2dm_3 = ('M2I1NXASM.5.12.4/','/MERRA2_300.inst1_2d_asm_Nx.')            # sub url of 2d Single-Level Diagnostics     
        baseurl_2dr_3 = ('M2T1NXRAD.5.12.4/','/MERRA2_300.tavg1_2d_rad_Nx.')            # sub url of 2d radiation Diagnostics data 
        baseurl_2ds_3 = ('M2T1NXFLX.5.12.4/','/MERRA2_300.tavg1_2d_flx_Nx.')            # sub url of 2d suface flux Diagnostics data                                                                             
        baseurl_2dv_3 = ('M2T1NXSLV.5.12.4/','/MERRA2_300.tavg1_2d_slv_Nx.')            # sub url of 2d 1-Hourly,Time-Averaged,Single-Level,Assimilation,Single-Level Diagnostics V5.12.4                                                                                                                                                                                                  
        # 2011 ~ present
        baseurl_3dn_4 = ('M2I6NPANA.5.12.4/','/MERRA2_400.inst6_3d_ana_Np.')            # sub url of 3d Pressure Levels Analyzed Meteorological Fields data      
        baseurl_3da_4 = ('M2I3NPASM.5.12.4/','/MERRA2_400.inst3_3d_asm_Np.')            # sub url of 3d Pressure Levels Assimilated Meteorological Fields data 
        baseurl_2dm_4 = ('M2I1NXASM.5.12.4/','/MERRA2_400.inst1_2d_asm_Nx.')            # sub url of 2d Single-Level Diagnostics      
        baseurl_2dr_4 = ('M2T1NXRAD.5.12.4/','/MERRA2_400.tavg1_2d_rad_Nx.')            # sub url of 2d radiation Diagnostics data 
        baseurl_2ds_4 = ('M2T1NXFLX.5.12.4/','/MERRA2_400.tavg1_2d_flx_Nx.')            # sub url of 2d suface flux Diagnostics data                                                         
        baseurl_2dv_4 = ('M2T1NXSLV.5.12.4/','/MERRA2_400.tavg1_2d_slv_Nx.')            # sub url of 2d 1-Hourly,Time-Averaged,Single-Level,Assimilation,Single-Level Diagnostics V5.12.4                                                                                                                                                                                                  

                
        format = ('.nc4')
                        
        #Setup the start and end of dates
        Begin = date['beg']
        End  =  date['end']
                
        #Setup the based string of dates for urls 
        res1 = [d.strftime("%Y/%m") for d in pandas.date_range(Begin,End)]
        res2 = [d.strftime("%Y%m%d") for d in pandas.date_range(Begin,End)]        
            
       # get the urls list
       
        urls_3dmana = []
        urls_3dmasm = []
        urls_2dm = []
        urls_2dr = []
        urls_2ds = []
        urls_2dv = []
        for i in range(0,len(res1)):
                 if res1[i] >= '1980/01' and res1[i] <= '1991/12':  
                    urls_3dmana.append(baseurl_3d + baseurl_3dn_1[0] + res1[i] + baseurl_3dn_1[1] + res2[i] + format)  # urls of 3d Analyzed Meteorological Fields datasets with temporal subset(1980 ~ 1991)            
                    urls_3dmasm.append(baseurl_3d + baseurl_3da_1[0] + res1[i] + baseurl_3da_1[1] + res2[i] + format)  # urls of 3d Assimilated Meteorological Fields datasets with temporal subset (1980 ~ 1991)                  
                    urls_2dm.append(baseurl_2d + baseurl_2dm_1[0] + res1[i] + baseurl_2dm_1[1] + res2[i] + format)     # urls of 2d meteorological Diagnostics datasets temporal subset(1980 ~ 1991)  
                    urls_2ds.append(baseurl_2d + baseurl_2ds_1[0] + res1[i] + baseurl_2ds_1[1] + res2[i] + format)     # urls of 2d suface flux Diagnostics datasets with temporal subset (1980 ~ 1991)   
                    urls_2dr.append(baseurl_2d + baseurl_2dr_1[0] + res1[i] + baseurl_2dr_1[1] + res2[i] + format)     # urls of 2d radiation Diagnostics datasets with temporal subset(1980 ~ 1991) 
                    urls_2dv.append(baseurl_2d + baseurl_2dv_1[0] + res1[i] + baseurl_2dv_1[1] + res2[i] + format)     # urls of 2d Single-Level,Assimilation,Single-Level Diagnostics (1980 ~ 1991) 
                 elif res1[i] >= '1992/01' and res1[i] <= '2000/12':
                    urls_3dmana.append(baseurl_3d + baseurl_3dn_2[0] + res1[i] + baseurl_3dn_2[1] + res2[i] + format)  # urls of 3d Analyzed Meteorological Fields datasets with temporal subset (1992 ~ 2000)              
                    urls_3dmasm.append(baseurl_3d + baseurl_3da_2[0] + res1[i] + baseurl_3da_2[1] + res2[i] + format)  # urls of 3d Assimilated Meteorological Fields datasets with temporal subset (1992 ~ 2000)                 
                    urls_2dm.append(baseurl_2d + baseurl_2dm_2[0] + res1[i] + baseurl_2dm_2[1] + res2[i] + format)     # urls of 2d meteorological Diagnostics datasets temporal subset (1992 ~ 2000)
                    urls_2ds.append(baseurl_2d + baseurl_2ds_2[0] + res1[i] + baseurl_2ds_2[1] + res2[i] + format)     # urls of 2d suface flux Diagnostics datasets with temporal subset (1992 ~ 2000) 
                    urls_2dr.append(baseurl_2d + baseurl_2dr_2[0] + res1[i] + baseurl_2dr_2[1] + res2[i] + format)     # urls of 2d radiation Diagnostics datasets with temporal subset (1992 ~ 2000)
                    urls_2dv.append(baseurl_2d + baseurl_2dv_2[0] + res1[i] + baseurl_2dv_2[1] + res2[i] + format)     # urls of 2d Single-Level,Assimilation,Single-Level Diagnostics (1992 ~ 2000)
                 elif res1[i] >= '2001/01' and res1[i] <= '2010/12':
                    urls_3dmana.append(baseurl_3d + baseurl_3dn_3[0] + res1[i] + baseurl_3dn_3[1] + res2[i] + format)  # urls of 3d Analyzed Meteorological Fields datasets with temporal subset (2001 ~ 2010)              
                    urls_3dmasm.append(baseurl_3d + baseurl_3da_3[0] + res1[i] + baseurl_3da_3[1] + res2[i] + format)  # urls of 3d Assimilated Meteorological Fields datasets with temporal subset (2001 ~ 2010)                  
                    urls_2dm.append(baseurl_2d + baseurl_2dm_3[0] + res1[i] + baseurl_2dm_3[1] + res2[i] + format)     # urls of 2d meteorological Diagnostics datasets temporal subset (2001 ~ 2010) 
                    urls_2ds.append(baseurl_2d + baseurl_2ds_3[0] + res1[i] + baseurl_2ds_3[1] + res2[i] + format)     # urls of 2d suface flux Diagnostics datasets with temporal subset (2001 ~ 2010) 
                    urls_2dr.append(baseurl_2d + baseurl_2dr_3[0] + res1[i] + baseurl_2dr_3[1] + res2[i] + format)     # urls of 2d radiation Diagnostics datasets with temporal subset (2001 ~ 2010) 
                    urls_2dv.append(baseurl_2d + baseurl_2dv_3[0] + res1[i] + baseurl_2dv_3[1] + res2[i] + format)     # urls of 2d Single-Level,Assimilation,Single-Level Diagnostics (2001 ~ 2010)
                 elif res1[i] >= '2011/01':
                    urls_3dmana.append(baseurl_3d + baseurl_3dn_4[0] + res1[i] + baseurl_3dn_4[1] + res2[i] + format)  # urls of 3d Analyzed Meteorological Fields datasets with temporal subset (2011 ~ present)              
                    urls_3dmasm.append(baseurl_3d + baseurl_3da_4[0] + res1[i] + baseurl_3da_4[1] + res2[i] + format)  # urls of 3d Assimilated Meteorological Fields datasets with temporal subset (2011 ~ present)                   
                    urls_2dm.append(baseurl_2d + baseurl_2dm_4[0] + res1[i] + baseurl_2dm_4[1] + res2[i] + format)     # urls of 2d meteorological Diagnostics datasets temporal subset (2011 ~ present)   
                    urls_2ds.append(baseurl_2d + baseurl_2ds_4[0] + res1[i] + baseurl_2ds_4[1] + res2[i] + format)     # urls of 2d suface flux Diagnostics datasets with temporal subset (2011 ~ present)   
                    urls_2dr.append(baseurl_2d + baseurl_2dr_4[0] + res1[i] + baseurl_2dr_4[1] + res2[i] + format)     # urls of 2d radiation Diagnostics datasets with temporal subset (2011 ~ present)   
                    urls_2dv.append(baseurl_2d + baseurl_2dv_4[0] + res1[i] + baseurl_2dv_4[1] + res2[i] + format)     # urls of 2d Single-Level,Assimilation,Single-Level Diagnostics (2011 ~ present) 
        
     
        #Setup URL for getting constant model parameters (2D, single-level, full horizontal resolution)
        url_2dc = ['https://goldsmr4.gesdisc.eosdis.nasa.gov:443/opendap/MERRA2_MONTHLY/M2C0NXASM.5.12.4/1980/MERRA2_101.const_2d_asm_Nx.00000000.nc4']
 
        return urls_3dmana, urls_3dmasm, urls_2dm, urls_2ds, urls_2dr, url_2dc, urls_2dv
 
    def download(self, username, password, urls, chunk_size):
        """ Access the MERRA server by account information and defiend urls
            Args:
            username = "xxxxxx"
            password = "xxxxxx"
            urls = urls_3dmana,urls_3dmasm,urls_2dm,urls_2ds, urls_2dr: a full list of urls by specific date range of wanted types of dataset
            chunk_size: the wanted size of urls list for each chunk
            Return:
            ds: the each individual original dataset (The dictionary of basetype with children['variables']) 
                                                           of 3d Analyzed Meteorological Fields, 
                                                              3d Assimilated Meteorological Fields datasets,
                                                              2d meteorological Diagnostics datasets,
                                                              2d surface flux Diagnostics datasets,
                                                              2d radiation Diagnostics datasets
            ds_structure: [lengths of total_chunks * chunk_size]                                                                            
        """

        urls_chunks = [urls[x:x+chunk_size] for x in xrange(0, len(urls), chunk_size)]      

        print ('================ MERRA-2 SERVER ACCESS: START ================')
        print ('TIME TO GET A COFFEE')        
        ds = {}
        for i in range(len(urls_chunks)):
            ds[i] = {}
            url = urls_chunks[i]
            for j in range(len(url)): 
                # try downloading and repeat ten times before giving up
                for delay in range(0,60):
                    try: # try to download the file
                        session = setup_session(username, password, check_url=url[j])        
                        ds[i][j] = open_url(url[j], session=session)
                        break
                    except:
                        if delay < 59:
                            print "Error downloading file: " + url[j] + ". Trying again (" + str(delay) + ")"
                            sleep(delay)
                            pass
                        else:    
                            print "Error downloading file: " + url[j] + ". Giving up."
                            raise RuntimeError("==> Unsuccesfull after 60 attempts.")
                print ('------COMPLETED------','CHUNK NO.:', i+1, 'URL NO.:', j+1 )
                print url[j]
            print ds[i][j].keys    
        print ('================ MERRA-2 SERVER ACCESS: COMPLETED ================')
        infor = urls[0].split('/')
        print 'Dataset:', infor[2], infor[3],infor[4]
        print 'Type:', type(ds)
        print 'Days:', len(urls)    
        
        return ds        
    
    def Variables(self, variable, ds):
        """Get the objected variables from the specific MERRA-2 datasets        
           variable = ['T','U','V','H','lat','lon','lev','time']                                     # for extracting from 3d Analyzed Meteorological Fields datasets 
                    = ['RH','H','lat','lon','lev','time']                                     # for extracting from 3d Assimilated Meteorological Fields datasets
                    = ['U2M','T2M','TQL','V2M','V10M','U10M','QV2M','lat','lon','time']              # for extracting from 2d meteorological Diagnostics datasets
                    = ['PRECTOT','PRECTOTCOR', 'lat','lon','time']                                                 # for extracting from 2d suface flux Diagnostics datasets  
                    = ['SWGDN','LWGNT', 'SWGDNCLR', 'LWGNTCLR', 'LWGEM', 'lat','lon','time']         # for extracting from 2d radiation Diagnostics datasets 
                    = ['PHIS', 'FRLAND', 'FRLANDICE', 'lat', 'lon','time']                                                   # for extracing from 2d constant model parameters
                    
           ds = MERRAgeneric().download(username, password, urls_3dmana, urls_3dmasm, urls_2dm, urls_2ds, urls_2dr, chunk_size)
           Return:
           out_variable: The extracted variables in the order of given list 
                         Type: BaseType with the given data baseProxy
                         
           out_variable structure: [lenghs of total chunks * chunk_size * lenghs of variables]
           
        """

        out_variable = {}
        for i in range(0, len(ds)):
            out_variable[i] = {}
            for j in range(len(ds[i])):
                print "Run", "Chunk:", i+1, "NO.:", j+1
                outputVar = []
                for x in range(0,len(variable)):
                    outputVar.append(variable[x])

                var = ds[i][j].keys()
                for l in range(len(outputVar)):
                    foundVariable = False
                    if outputVar[l] in var:
                        for k in range(len(var)):
                            if foundVariable != True:
                                if var[k] == outputVar[l]:
                                    temp = "" + var[k]
                                    outputVar[l] = ds[i][j][temp]
                                    foundVariable = True
                out_variable[i][j] = outputVar

        print "Length of Out_Variable:", len(out_variable[0][0])
        
        return out_variable
    
    def getArea(self, area, ds): 
        """Gets the specific indexs  of the latitudes and longitudes of given area
           For example: 
           area = {'north':65.0, 'south': 60.0, 'west':-115.0, 'east': -110.0}
           ds = MERRAgeneric().download(username, password, urls_3dmana, urls_3dmasm, urls_2dm, urls_2dr, urls_2ds, chunk_size)
           Return:
           id_lat: wanted indexs of latitudes from the original merra global dataset
           id_lon: wanted indexs of longitudes from the original merra global dataset
        """
             
        # pass the value of individual row lat and lon to Lat and Lon for the area subset
        Lat = ds[0][0].lat[:]
        Lon = ds[0][0].lon[:]
                        
        # get the indices of selected range of Lat,Lon
        id_lon = np.where((Lon[:] >= area['west']) & (Lon[:] <= area['east'])) 
        id_lat = np.where((Lat[:] >= area['south']) & (Lat[:] <= area['north'])) 
       
        # convert id_lat, id_lon from tuples to string
        id_lon = list(itertools.chain(*id_lon))   
        id_lat = list(itertools.chain(*id_lat))

        
        return id_lat, id_lon 

    def getPressure(self, elevation):
        """Convert elevation into air pressure using barometric formula"""
        g  = 9.80665   #Gravitational acceleration [m/s2]
        R  = 8.31432   #Universal gas constant for air [N·m /(mol·K)]    
        M  = 0.0289644 #Molar mass of Earth's air [kg/mol]
        P0 = 101325    #Pressure at sea level [Pa]
        T0 = 288.15    #Temperature at sea level [K]
        #http://en.wikipedia.org/wiki/Barometric_formula
        return P0 * exp((-g * M * elevation) / (R * T0)) / 100 #[hPa] or [bar]
    
    def getPressureLevels(self, elevation): 
        """Restrict list of MERRA-2 pressure levels to be download"""
        Pmax = self.getPressure(elevation['min']) + 55
        Pmin = self.getPressure(elevation['max']) - 55
        # Pmax = self.getPressure(ele_min) + 55
        # Pmin = self.getPressure(ele_max) - 55
        levs = np.array([1000, 975, 950, 925, 900, 875, 850, 825, 800, 775, 750, 725, 700, 650, 600, 550, 500, 450, 400, 350, 300, 250, 200, 150, 100, 70,    
                          50, 40, 30, 20, 10, 7.0, 5.0, 4.0, 3.0, 2.0, 1.0, 0.7, 0.5, 0.4, 0.3, 0.1])
 
        #Get the indics of selected range of elevation 
        id_lev = np.where((levs >= Pmin) & (levs <= Pmax))
        id_lev = list(itertools.chain(*id_lev))    
                
        return id_lev
  
    def latLon_3d(self, out_variable, id_lat, id_lon, id_lev): 
        """
        Get Latitude, Longitude, Levels, and Time for datasets at the pressure levels
        Args:
        out_variable = MERRAgeneric().getVariables(variable, ds) 
        id_lat, id_lon =  MERRAgeneric().getArea(area, ds)
        -4 = id_Latitude
        -3 = id_Longitude
        -2 = id_Level
        -1 = id_Time 
        Return: 
        lat, lon, lev, time: the extracted latitudes, longitudes in the given area from 3D original dateset
        lat_structure: lengths of total_chunks * chunk_size * lengths of extracted latitudes
        lon_structure: lengths of total_chunks * chunk_size * lengths of extracted longitudes
        lev_structure: lengths of total_chunks * chunk_size * total number of pressure levels from original dataset 
        time_structure: lengths of total_chunks * chunk_size * total number of hours per day from original dataset                                        
        """   
   
        Lat  = {}
        Lon  = {}
        Lev  = {}
        time = {}
        for i in range(0, len(out_variable)):
            Lat[i] = {}
            Lon[i] = {}
            Lev[i] = {}
            time[i] = {}
            for j in range(0, len(out_variable[i])):
                for delay in range(0,60):
                    try: # try to obtain the data of Lat, Lon, Lev, time each by each
                        print "run", "Chunk:", i+1, "NO.:", j+1
                        Lat[i][j]   = out_variable[i][j][-4][:]
                        Lon[i][j]   = out_variable[i][j][-3][:]
                        Lev[i][j]   = out_variable[i][j][-2][:]
                        time[i][j]  = out_variable[i][j][-1][:]
                        break
                    except:
                        if delay < 59:
                            print "Error downloading data: " + ". Trying again (" + str(delay) + ")"
                            sleep(delay)
                            pass
                        else:    
                            print "Error downloading data: " + ". Giving up."
                            raise RuntimeError("==> Unsuccesfull after 60 attempts.")
                
        #For Latitude and Longitude   
        lat = {}
        lon = {}               
        for i in range(0, len(Lat)):
            lat[i] = {}
            lon[i] = {}       
            for j in range(len(Lat[i])):
                lat[i][j] = Lat[i][j][id_lat]                
                lon[i][j] = Lon[i][j][id_lon]

        #For elevation 
        lev = {}               
        for i in range(0, len(Lev)):
            lev[i] = {}    
            for j in range(len(Lev[i])):
                
                lev[i][j] = Lev[i][j][id_lev]                       
         
        return lat, lon, lev, time    

    def latLon_2d(self, out_variable, id_lat, id_lon): 
        """
        Get Latitude, Longitude, Levels, and Time for datasets at surface level
        Args:
        out_variable = MERRAgeneric().getVariables(variable, ds) 
        id_lat, id_lon =  MERRAgeneric().getArea(area, ds)
        -3 = id_Latitude
        -2 = id_Longitude
        -1 = id_Time 
        Return:
        lat, lon, lev, time: the extracted latitudes, longitudes in the given area from 2D original dateset
        lat_structure: length of total_chunks * chunk_size * lengths of extracted latitudes
        lon_structure: length of total_chunks * chunk_size * lengths of extracted longitudes
        time_structure: length of total_chunks * chunk_size * total number of hours per day from original dataset                               
        """
   
        Lat  = {}
        Lon  = {}
        time = {}
        for i in range(0, len(out_variable)):
            Lat[i] = {}
            Lon[i] = {}
            time[i] = {}
            for j in range(0, len(out_variable[i])):
                for delay in range(0,60):
                    try: # try to obtain the data of Lat, Lon, time each by each
                        print "Run", "Chunk:",i+1, "NO.:", j+1
                        Lat[i][j]   = out_variable[i][j][-3][:]
                        Lon[i][j]   = out_variable[i][j][-2][:]
                        time[i][j]  = out_variable[i][j][-1][:]
                        break
                    except:
                        if delay < 59:
                            print "Error downloading data: " + ". Trying again (" + str(delay) + ")"
                            sleep(delay)
                            pass
                        else:    
                            print "Error downloading data: " + ". Giving up."
                            raise RuntimeError("==> Unsuccesfull after 60 attempts.")
                
        #For Latitude and Longitude 
        lat = {}
        lon = {}               
        for i in range(0, len(Lat)):
            lat[i] = {}
            lon[i] = {}       
            for j in range(len(Lat[i])):
                lat[i][j] = Lat[i][j][id_lat]                
                lon[i][j] = Lon[i][j][id_lon]
        
        return lat, lon, time

    def dataStuff_3d(self, position, id_lat, id_lon, id_lev, out_variable):  
        """Define the outputs ones &
           pass the values of abstrated variables to the output ones and 
           restrict the area 
           Args:
           id_lat, id_lon =  MERRAgeneric().getArea(area, ds) 
           position: index of the variable in get_variables (setup automatically)

           3d Analyzed Meteorological Fields datasets:
           t = MERRAgeneric().dataStuff(position, lat, lon, lev, time, id_lat, id_lon, out_variable)
           u = MERRAgeneric().dataStuff(position, lat, lon, lev, time, id_lat, id_lon, out_variable)
           v = MERRAgeneric().dataStuff(position, lat, lon, lev, time, id_lat, id_lon, out_variable)
           h = MERRAgeneric().dataStuff(position, lat, lon, lev, time, id_lat, id_lon, out_variable)
           
           3d Assimilated Meteorological Fields datasets:
           rh = MERRAgeneric().dataStuff(position, lat, lon, lev, time, id_lat, id_lon, out_variable)    
                  
           Return:
           data_area: the extracted individual variable at pressure levels at the given area
           data_area_Structure: length of total_chunks * chunk_size * [time*level*lat*lon]
        """
        print "Get Data"
        data = {}
        for i in range(0, len(out_variable)):
            data[i] = {}
            for j in range(0, len(out_variable[i])):
                for delay in range(0,60):
                    try: # try to obtain the data of variable each by each
                         print "Run","Chunk", i+1, "NO.:", j+1 
                         data[i][j] = out_variable[i][j][position][:]
                         break
                    except:
                        if delay < 59:
                            print "Error downloading data: " + ". Trying again (" + str(delay) + ")"
                            sleep(delay)
                            pass
                        else:    
                            print "Error downloading data: " + ". Giving up."
                            raise RuntimeError("==> Unsuccesfull after 60 attempts.")
                             
        # Restrict the area for data set
        print "Restrict Area and Elevation"
        data_area = {}
        for i in range(0, len(data)): 
            data_area[i] = {}
            for j in range(0, len(data[i])):
                print "Run", "Chunk", i+1, "NO.:", j+1
                data_area[i][j] = data[i][j][:,id_lev,:,:]  
            for j in range(0, len(data_area[i])):
                data_area[i][j] = data_area[i][j][:,:,id_lat,:]
            for j in range(0, len(data_area[i])):
                data_area[i][j] = data_area[i][j][:,:,:,id_lon]
            
        del data 

        return data_area

        
    def dataStuff_2d(self, position, id_lat, id_lon, out_variable):  
        """Define the outputs ones &
           pass the values of abstrated variables to the output ones and 
           restrict the area 
         Args:            
           id_lat, id_lon =  MERRAgeneric().getArea(area, ds) 
           position: index of the variable in get_variables (setup automatically)
          
           2d meteorological Diagnostics datasets:
           t2m = MERRAgeneric().dataStuff_2d(position, lat, lon, time, id_lat, id_lon, out_variable)
           u2m = MERRAgeneric().dataStuff_2d(position, lat, lon, time, id_lat, id_lon, out_variable)
           v2m = MERRAgeneric().dataStuff_2d(position, lat, lon, time, id_lat, id_lon, out_variable)       
           u10m = MERRAgeneric().dataStuff_2d(position, lat, lon, time, id_lat, id_lon, out_variable)
           v10m = MERRAgeneric().dataStuff_2d(position, lat, lon, time, id_lat, id_lon, out_variable)
           
           2d suface flux Diagnostics datasets:
           prectot = MERRAgeneric().dataStuff_2d(position, lat, lon, time, id_lat, id_lon, out_variable
           
           2d radiation Diagnostics datasets:
           t2m = MERRAgeneric().dataStuff_2d(position, lat, lon, time, id_lat, id_lon, out_variable)
           u2m = MERRAgeneric().dataStuff_2d(position, lat, lon, time, id_lat, id_lon, out_variable)
           
           2d constant model parameters
           phis = MERRAgeneric().dataStuff_2d(position, lat, lon, time)
           
           Return:
           data_area: the extracted individual variable at surface levels at the given area
           data_area_structure: length of total_chunks * chunk_size * [time*lat*lon]
           
        """
        print "Get Data"
        data = {}
        for i in range(0, len(out_variable)):
            data[i] = {}
            for j in range(0, len(out_variable[i])):
                for delay in range(0,60):
                    try: # try to obtain the data of variable each by each
                        print "Run","Chunk", i+1, "NO.:", j+1
                        data[i][j] = out_variable[i][j][position][:]
                        break
                    except:
                        if delay < 59:
                            print "Error downloading data: " + ". Trying again (" + str(delay) + ")"
                            sleep(delay)
                            pass
                        else:    
                            print "Error downloading data: " + ". Giving up."
                            raise RuntimeError("==> Unsuccesfull after 60 attempts.")
                    
        # Restrict the area for data set
        print "Restrict Area"
        data_area = {}
        for i in range(0, len(data)): 
            data_area[i] = {}
            for j in range(0, len(data[i])):
                print "Run","Chunk", i+1, "NO.:", j+1
                data_area[i][j] = data[i][j][:,id_lat,:]
            for j in range(0, len(data_area[i])):
                data_area[i][j] = data_area[i][j][:,:,id_lon]
            
        del data 

        return data_area
        
    def getTime(self, date):                                                                                                                                          
        """set up date and time series for netCDF output results 
            Return: 
            date_ind: a string list of date in the range of begin and end (format: yearmonthday)
            time_ind1: the time series for 6-hours step in the range of begin and end dates  
            time_ind2: the time series for 3-hours step in the range of begin and end dates
            time_ind3: the time series for 1-hour step in the range of begin and end dates
        """ 
        
        Start = date['beg']
        End   = date['end']
 
        # Set up the wanted time step
        time_step1 = '6H'
        time_step2 = '3H'
        time_step3 = '1H'
            
        #get extra one one more day for getting the full range of time series
        End1 = End + timedelta(days=1)           
            
        #get the Datetimeindex with time_step 
        time_ind1 = (pandas.date_range(Start, End1, freq = time_step1))[0:-1]       
        time_ind2 = (pandas.date_range(Start, End1, freq = time_step2))[0:-1] 
        time_ind3 = (pandas.date_range(Start, End1, freq = time_step3))[0:-1]

        # To Datetime Objects
        time_ind1.to_datetime()
        time_ind2.to_datetime()
        time_ind3.to_datetime()
                                 
        # get list of wanted date series
        date_diff = End - Start
        date_ind = [Start + timedelta(days=x) for x in range(date_diff.days + 1)]
        date_ind = [d.strftime('%Y%m%d') for d in date_ind]

        return date_ind, time_ind1, time_ind2, time_ind3
 
    def restruDatastuff(self, data_area):                                                                                                                                          
        """ Restructuring the dimension of abstracted data stuff for preparing to save netCDF output results furtherly
            return: 
            data_total: for 3d: (len(date)*len(time/day), level, lat, lon)
                        for 2d: (len(date)*len(time/day), lat, lon)
        """ 
        data_total = []                                                   
        for i in range(0, len(data_area)):                                           
            for j in range(0,len(data_area[i])):
                for k in range(0,len(data_area[i][j])):
                    data_total.append(data_area[i][j][k][:])
        
        data_total = np.asarray(data_total, dtype = float)

        return data_total
        
    def tempExtrapolate(self, t_total, h_total, elevation):
        """ Processing 1D vertical extrapolation for Air Temperature at specific levels, 
            at where the values are lacking  (marked by 9.9999999E14) from merra-2 3d Analyzed Meteorological Fields datasets
            IMPORTANT TIP: to set up 'ele_max = 2500' (meter) or higher
                           reason: to make sure get enough levels of geopotential height 
                           for conducting 1dinterp (linear)(2 points of values needed at least)          
        """  

        #restructure t_total [time*lev*lat*lon] to [lat*lon*time*lev]
        t_total = t_total[:,:,:,:].transpose((2,3,0,1))
        h_total = h_total[:,:,:,:].transpose((2,3,0,1))

        #find the value gap and conduct 1d extrapolation 
        for i in range(0, len(t_total)): 
            for j in range(0, len(t_total[0])):
                 t_time = t_total[i][j][:]
                 h_time = h_total[i][j][:]
                 for k in range(0, len(t_time)) :
                     t_lev = t_time[k][:]
                     h_lev = h_time[k][:]
                     id_interp = [] 
                     for z in range(0, len(t_lev)):
                         # find the indice of levels with missing values
                         if t_lev[z] > 99999:
                            id_interp.append(z)

                            if id_interp != []:
                                # get the levels of geopotential heights with missing values
                                lev_interp = h_lev[id_interp]
                                # pass the index of first found level with existing value to z_top
                                z_top = id_interp[-1] + 1
                                #get values at the lowest 3 levels of geopotential heights with existed values
                                lev_3p = h_lev[z_top:z_top + 3]
                                #get values at the lowest 3 levels of air temperature with existed values
                                t_3p = t_lev[z_top:z_top + 3]
                                #Using spicy.interpolate.interp1d function-------------------------
                                # Require >= 2 points of levs and t in minimum
                                if len(lev_3p) >= 2:
                                    # build linear function based on given values at lowest 3 levels of air temperature and geopotential heights
                                    f = interp1d(lev_3p, t_3p, kind = 'linear', fill_value = 'extrapolate')
                                    # use built function to calculate the values of air temperature at the found missing-values levels
                                    t_interp = f(lev_interp)    
                                    # fill the calcaulated values into missing-values levels
                                    t_lev[id_interp] = t_interp
                                else:
                                    print 'Numbers of points for extrapolation are too low (less then 2):', len(lev_3p)
                                    print 'Failed to conduct extrapolation at some points in the output'
                                    print 'Current ele_max =', elevation['max']
                                    print 'Higher Value of "ele_max" is needed to reset: > 2500'
                                    sys.exit(0)    
        
                         else: 
                            t_lev[z] = t_lev[z]           
                         h_lev[z] = h_lev[z]
                     
                     #assign back                       
                     t_time[k][:] = t_lev
                     h_time[k][:] = h_lev

                 #replace the extrapolated value [time * level] to each individual cell
                 t_total[i][j][:] = t_time
                 h_total[i][j][:] = h_time  
                                                 
        #restructure back    
        t_total = t_total[:,:,:,:].transpose((2,3,0,1))
        h_total = h_total[:,:,:,:].transpose((2,3,0,1))
            
        return t_total
                         
    def windExtrapolate(self, wind_total):
        """Processing 1D vertical extraplation for wind components at specific levels, 
            at where the values are lacking (marked by 9.9999999E14) from merra-2 3d Analyzed Meteorological Fields datasets
            Wind (u,v) are utilized the value of at lowest pressure levels to the ones with value gaps
        """ 

        #restructure u_total,v_total [time*lev*lat*lon] to [lat*lon*time*lev]
        wind_total = wind_total[:,:,:,:].transpose((2,3,0,1))

        #find and fill the value gap  
        for i in range(0, len(wind_total)):
            for j in range(0,len(wind_total[0])):
                wind_time = wind_total[i][j][:]
                for k in range(0,len(wind_time)):
                    wind_lev = wind_time[k][:]
                    id_interp = [] 
                    for z in range(0, len(wind_lev)):
                        if wind_lev[z] > 99999:
                           id_interp.append(z)

                        if id_interp != []: 
                            z_top = id_interp[-1] + 1
                            wind_lev[id_interp] = wind_lev[z_top]
                        else: 
                            wind_lev[z] = wind_lev[z]           
                                           
                    wind_time[k][:] = wind_lev

                #replace the interpoaltion value to each single pixel
                wind_total[i][j][:] = wind_time
                           
        #restructure back    
        wind_total = wind_total[:,:,:,:].transpose((2,3,0,1))
               
        return wind_total
       
    def rhExtrapolate(self, rh_total):
        """Processing 1D vertical extrapolation for relative humidity at specific levels,
            at where the values are lacking (marked by 9.9999999E14) from merra-2 3d Assimilated Meteorological Fields datasets
            Relative Humidity (rh) is utilized the value of at lowest pressure level to the ones with value gaps
        """     
        #restructure rh_total [time*lev*lat*lon] to [lat*lon*time*lev]
        rh_total = rh_total[:,:,:,:].transpose((2,3,0,1))

        #find and fill the value gap  
        for i in range(0, len(rh_total)):
            for j in range(0,len(rh_total[0])):
                rh_time = rh_total[i][j][:]
                for k in range(0,len(rh_time)):
                    rh_lev = rh_time[k][:]
                    id_interp = [] 
                    for z in range(0, len(rh_lev)):
                        if rh_lev[z] > 99999:
                           id_interp.append(z)

                        if id_interp != []: 
                            z_top = id_interp[-1] + 1
                            rh_lev[id_interp] = rh_lev[z_top]
                        else: 
                            rh_lev[z] = rh_lev[z]           
                                           
                    rh_time[k][:] = rh_lev

                #replace the interpoaltion value to each single pixel
                rh_total[i][j][:] = rh_time

        #restructure back    
        rh_total = rh_total[:,:,:,:].transpose((2,3,0,1))
        
        return rh_total

    def MERRA_skip(self, merralist):
        '''
        To remove the extra variables from downloaded MERRA2 data
        '''
        for x in merralist:
            if x == 'PRECTOT':
               merralist.remove('PRECTOT')
            if x == 'LWGAB': 
               merralist.remove('LWGAB')
               merralist.remove('LWGABCLR')
               merralist.remove('LWGEM')
               merralist.remove('LWGNT')
               merralist.remove('LWGNTCLR')

        for x in merralist:
              if  x == 'DIFF_LWGDN_LWGAB':  
                 merralist.remove('DIFF_LWGDN_LWGAB')
                 merralist.remove('DIFF_LWGDNCLR_LWGABCLR')
        
        return merralist
                      
    def netCDF_empty(self, ncfile_out, stations, nc_in):
        '''
        Creates an empty station file to hold interpolated reults. The number of 
        stations is defined by the variable stations, variables are determined by 
        the variable list passed from the gridded original netCDF.
        
        ncfile_out: full name of the file to be created
        stations:   station list read with generic.StationListRead() 
        variables:  variables read from netCDF handle
        lev:        list of pressure levels, empty is [] (default)
        '''
        
        #Build the netCDF file
        rootgrp = nc.Dataset(ncfile_out, 'w', format='NETCDF4_CLASSIC')
        rootgrp.Conventions = 'CF-1.6'
        rootgrp.source      = 'MERRA-2, interpolated bilinearly to stations'
        rootgrp.featureType = "timeSeries"
                                                
        # dimensions
        station = rootgrp.createDimension('station', len(stations))
        time    = rootgrp.createDimension('time', None)
                
        # base variables
        time           = rootgrp.createVariable('time', 'i4',('time'))
        time.long_name = 'time'
        time.units     = 'hour since 1980-01-01 00:00:0.0'
        time.calendar  = 'gregorian'
        station             = rootgrp.createVariable('station', 'i4',('station'))
        station.long_name   = 'station for time series data'
        station.units       = '1'
        latitude            = rootgrp.createVariable('latitude', 'f4',('station'))
        latitude.long_name  = 'latitude'
        latitude.units      = 'degrees_north'    
        longitude           = rootgrp.createVariable('longitude','f4',('station'))
        longitude.long_name = 'longitude'
        longitude.units     = 'degrees_east' 
        height           = rootgrp.createVariable('height','f4',('station'))
        height.long_name = 'height_above_reference_ellipsoid'
        height.units     = 'm'  
        
        # assign station characteristics            
        station[:]   = list(stations['station_number'])
        latitude[:]  = list(stations['latitude_dd'])
        longitude[:] = list(stations['longitude_dd'])
        height[:]    = list(stations['elevation_m'])
        
        # extra treatment for pressure level files
        try:
            lev = nc_in.variables['level'][:]
            print "== 3D: file has pressure levels"
            level = rootgrp.createDimension('level', len(lev))
            level           = rootgrp.createVariable('level','i4',('level'))
            level.long_name = 'pressure_level'
            level.units     = 'hPa'  
            level[:] = lev 
        except:
            print "== 2D: file without pressure levels"
            lev = []
        
        #remove extra varlables
        varlist_merra = [x.encode('UTF8') for x in nc_in.variables.keys()]
        varlist_merra = self.MERRA_skip(varlist_merra)                
        
        # create and assign variables based on input file
        for n, var in enumerate(varlist_merra):
            if variables_skip(var):
                continue
                                 
            print "VAR: ", var            
            # extra treatment for pressure level files        
            if len(lev):
                tmp = rootgrp.createVariable(var,'f4',('time', 'level', 'station'))
            else:
                tmp = rootgrp.createVariable(var,'f4',('time', 'station'))     
            tmp.long_name = nc_in.variables[var].standard_name.encode('UTF8') # for merra2
            tmp.units     = nc_in.variables[var].units.encode('UTF8')  
                    
        #close the file
        rootgrp.close()

    def netCDF_merge(self, directory):
        """
        To combine mutiple downloaded merra2 netCDF files into a large file with specified chunk_size(e.g. 500), 
        -- give the full name of merged file to the output = outfile
        -- pass all data from the first input netfile to the merged file name
        -- loop over the files_list, append file one by one into the merge file
        -- pass the mergae netcdf file to interpolation module to process( to use nc.MFDataset by reading it)
        
        Args:
            ncfile_in: the full name of downloaded files (file directory + files names)
        e.g.:
             '/home/xquan/src/globsim/examples/merra2/merra_sa_*.nc' 
             '/home/xquan/src/globsim/examples/merra2/merra_pl_*.nc'
             '/home/xquan/src/globsim/examples/merra2/merra_sf_*.nc'

        Output: merged netCDF files
        merra2_all_0.nc, merra2_all_1.nc, ...,
               
        """
        #set up nco operator
        nco = Nco()
  
        # loop over filetypes, read, report
        file_type = ['merra_sa_*.nc', 'merra_sf_*.nc', 'merra_pl_*.nc']
        for ft in file_type:
            ncfile_in = path.join(directory, ft)
            
            #get the file list
            files_list = glob.glob(ncfile_in)
            files_list.sort()
            num = len(files_list)
                        
            #set up the name of merged file
            if ncfile_in[-7:-5] == 'sa':
                merged_file = path.join(ncfile_in[:-11],'merra2_sa_all_'+ files_list[0][-23:-15] + "_" + files_list[num-1][-11:-3] +'.nc')
            elif ncfile_in[-7:-5] == 'sf':
                merged_file = path.join(ncfile_in[:-11],'merra2_sf_all_' + files_list[0][-23:-15] + '_' + files_list[num-1][-11:-3] + '.nc')
            elif ncfile_in[-7:-5] == 'pl':
                merged_file = path.join(ncfile_in[:-11],'merra2_pl_all_'+ files_list[0][-23:-15] + '_' + files_list[num-1][-11:-3] +'.nc')
            else:
                print 'There is not such type of file'    
                        
            # combined files into merged files
            nco.ncrcat(input=files_list,output=merged_file, append = True)
            
            print 'The Merged File below is saved:'
            print merged_file
            
            #clear up the data
            for fl in files_list:
                remove(fl)
                                                                                                                                                     
class MERRApl_ana():
    """Returns variables from downloaded MERRA 3d Analyzed Meteorological Fields datasets  
       which are abstracted with specific temporal and spatial range  
       
    Args:
        beg, end: A dictionary specifying the specific date desired as a datetime.datetime object.
              
        area: A dictionary delimiting the area to be queried with the latitudes
              north and south, and the longitudes west and east [decimal deg],to get 
              the indies of defined latitudes and longitudes.  
                      
        get_variables:  List of variable(s) to download that can include one, several
                   , or all of these: ['T','U','V',''H','lat','lon','lev','time']
        
              
    """
    
    def getDs(self, date, username, password, chunk_size):
        """Return the orginal datasets structured with defined chuncks form the specific MERRA-2 3d Analyzed Meteotological 
           Fields data products
           Args:
           username = ******
           password = ******
           chunk_size = 5
           ds = MERRAgeneric().download(username, password, urls, chunk_size)
        """    

        urls_3dmana, urls_3dmasm, urls_2dm, urls_2ds, urls_2dr, url_2dc, urls_2dv = MERRAgeneric().getURLs(date)
        urls = urls_3dmana
        
        ds = MERRAgeneric().download(username, password, urls, chunk_size)
        
        return ds
    
    def getVariables(self, get_variables, ds):                                    
        """Return the objected variables from the specific MERRA-2 3D Analyzed Meteorological Fields datasets        
           Args:
           ds = MERRAgeneric().download( username, password, urls_3dmana, size)
           
        """
        out_variable_3dmana = MERRAgeneric().Variables(get_variables, ds)

        return out_variable_3dmana 
        
    def getlatLon_3d (self, area, ds, elevation, out_variable_3dmana, id_lat, id_lon, id_lev):
        # old: def getlatLon (self, area, ds, out_variable_3dmana, p1, p2, p3, p4, id_lat, id_lon):
        """
        Return the objected Latitude, Longitude, Levels, Time from specific MERRA-2 3D datasets
        Args:
            id_lat, id_lon =  MERRAgeneric().getArea(area, ds)
            out_variable_3dmana = MERRAgeneric().getVariables(variable, ds)
            p1 = -4 (id_Latitude)
            p2 = -3 (id_Longitude)
            p3 = -2 (id_Level)
            p4 = -1 (id_Time)  

        """       
            
        id_lat, id_lon =  MERRAgeneric().getArea(area, ds)
        
        id_lev = MERRAgeneric().getPressureLevels(elevation)

        lat, lon, lev, time = MERRAgeneric().latLon_3d(out_variable_3dmana, id_lat, id_lon, id_lev)
        
        return lat, lon, lev, time
    

class MERRApl_asm():
    """Returns variables from downloaded MERRA 3d Assimilated Meteorological Fields data, 
       which are abstracted with specific temporal and spatial range        

    Args:
        date: A dictionary specifying the specific date desired as a datetime.datetime object.
              
        area: A dictionary delimiting the area to be queried with the latitudes
              north and south, and the longitudes west and east [decimal deg],to get 
              the indies of defined latitudes and longitudes.  
        
        variable:  List of variable(s) to download that can include one, several
                   , or all of these: ['RH','lat','lon','lev','time']
        

    """

    def getDs(self, date, username, password, chunk_size):
        """Return the orginal datasets structured with defined chuncks form the specific MERRA-2 3d Analyzed Meteotological 
           Fields data products
           Args:
           username = ******
           password = ******
           urls = urls_3dmasm
           chunk_size = 5
           ds = MERRAgeneric().download(username, password, urls, chunk_size)
        """    
        
        urls_3dmana, urls_3dmasm, urls_2dm, urls_2ds, urls_2dr, url_2dc, urls_2dv = MERRAgeneric().getURLs(date)
        urls = urls_3dmasm
        ds = MERRAgeneric().download(username, password, urls, chunk_size)
        return ds
        

    def getVariables(self, get_variables, ds):
        """Return the objected variables from the specific MERRA-2 3D datasets        
            get_variables = ['RH','lat','lon','lev','time']
            ds = MERRAgeneric.download( username, password, urls_3dmasm, chunk_size)
        """
        out_variable_3dmasm = MERRAgeneric().Variables(get_variables, ds)

        return out_variable_3dmasm
        
    def getlatLon_3d (self, area, ds, elevation, out_variable_3dmasm, id_lat, id_lon, id_lev): 
        """
        Return the objected Latitude, Longitude, Levels, Time from specific MERRA-2 3D datasets
        Args:
            id_lat, id_lon =  MERRAgeneric().getArea(area, ds)
            out_variable_3dmasm = MERRAgeneric().getVariables(variable, ds)
            p1 = -4 (id_Latitude)
            p2 = -3 (id_Longitude)
            p3 = -2 (id_Level)
            p4 = -1 (id_Time)  

        """       
        
        id_lat, id_lon =  MERRAgeneric().getArea(area, ds)
        
        id_lev = MERRAgeneric().getPressureLevels(elevation)
        
        lat, lon, lev, time = MERRAgeneric().latLon_3d(out_variable_3dmasm, id_lat, id_lon, id_lev)
        
        return lat, lon, lev, time
        

class SaveNCDF_pl_3dmana():                                                         # for saving abstracted pressure-levels variables
        """ write output netCDF file for abstracted variables from original meteorological data 
            at pressure levels
            demension: time, level, lat, lon
            variables: time: array([   0,  360,  720, 1080], dtype=int32, Unit:minute)
                       air temperature(time,lev,lat,lon), 
                       U component of wind(time,lev,lat,lon), 
                       V component of wind(time,lev,lat,lon),
                       geopotential heights(time,lev,lat,lon)
                       time, level, lat, lon.
            Args: 
            dir_data  = path.join(project_directory, "merra2/downloaded")  
            date, time_ind1 = MERRAgeneric().getTime(beg, end)
            t = MERRAgeneric().dataStuff_3d(position, id_lat, id_lon, out_variable_3dmana) 
            u = MERRAgeneric().dataStuff_3d(position,  id_lat, id_lon, out_variable_3dmana)
            v = MERRAgeneric().dataStuff_3d(position, id_lat, id_lon, out_variable_3dmana)
            h = MERRAgeneric().dataStuff_3d(position, id_lat, id_lon, out_variable_3dmana)        
            lat, lon, lev, time = MERRAgeneric().latLon(out_variable_3dmana, id_lat, id_lon)
                     
        """
  
        def saveData(self, date, get_variables, id_lat, id_lon, id_lev, out_variable_3dmana, chunk_size, time, lev, lat, lon, dir_data, rh_total,elevation):
        # creat a NetCDF file for saving output variables (Dataset object, also the root group).
            """
            Args: 
            dir_data  = path.join(project_directory, "merra2") 
                               
            """
            date_ind, time_ind1,time_ind2, time_ind3 = MERRAgeneric().getTime(date)
            
            #Setup size of saving file
            date_size = len(date_ind)
            
            # for t,v, u, h
            hour_size = len(time[0][0])
            int_size = date_size//chunk_size
            res_type = (date_size*hour_size)%(chunk_size*hour_size)
            
            if (res_type > 0):
                size_type = [chunk_size*hour_size]*int_size + [res_type]
            
            else:
                size_type = [chunk_size*hour_size]*int_size           

            #Get the wanted variables and Set up the list of output variables
            h_total = []
            t_total = []
            u_total = []
            v_total = []

            var_out = {'H':['geopotential_height','geopotential_height', 'm', h_total],
                       'T':['air_temperature', 'air_temperature','K', t_total],
                       'U':['eastward_wind','eastward_wind_component','m/s', u_total],
                       'V':['northward_wind','northward_wind_component', 'm/s', v_total]}            
            
            var_list = []
            for i in range(0, len(get_variables[0:-4])):
                for x in var_out.keys():
                    if x == get_variables[i]:
                        print ("------Get Subset of Variable at Pressure Levels------", get_variables[i])
                        var = MERRAgeneric().dataStuff_3d(i, id_lat, id_lon, id_lev, out_variable_3dmana)
                        # restructing the shape 
                        var_total = MERRAgeneric().restruDatastuff(var)
                        del var
                        if x == 'H':
                           h_total = var_total
                        elif x == 'T':
                           t_total = var_total
                           print "Conduct 1D Extrapolation for 'T'"
                           var_total = MERRAgeneric().tempExtrapolate(t_total, h_total, elevation) # 1D Extrapolation for Air Temperature
                        elif x == 'U': 
                           u_total = var_total
                           print "Conduct 1D Extrapolation for 'U'"                                       
                           var_total = MERRAgeneric().windExtrapolate(u_total)   #1D Extrapolation for Eastward Wind
                        elif x == 'V':
                           v_total = var_total
                           print "Conduct 1D Extrapolation for 'V'"
                           var_total = MERRAgeneric().windExtrapolate(v_total)   #1D Extrapolation for Northward Wind
                        
                        var_out[x][3] = var_total
                        
                        var_list.append([get_variables[i],var_out[x][0], var_out[x][1], var_out[x][2], var_out[x][3]])
            
            # Extracting RH at same time indice as geopotential height 
            # rh_total[double_time, level, lat, lon] to rh_total[even position of time, level, lat, lon]            
            rh_total = rh_total[::2,:,:,:]
            
            # Added Relative Humidity into output of variable list
            var_list.append(['RH','relative_humidity', 'relative humidity','1', rh_total])

            # save nc file 
            var_low = 0
            var_up = 0
            for i in range(0, 1):
            #for i in range(0, len(size_type)):
                var = size_type[i]
                var_low = var_up
                var_up = var_low + var
                
                #set up file path and names 
                file_ncdf  = path.join(dir_data,("merra_pl" + "_" + (date_ind[var_low/len(time[0][0])]) + "_" + "to" + "_" +(date_ind[var_up/len(time[0][0]) - 1]) + ".nc"))      
                rootgrp = Dataset(file_ncdf, 'w', format='NETCDF4_CLASSIC')
                print("Saved File Type:", rootgrp.file_format)
                rootgrp.source      = 'Merra, abstrated meteorological variables from metadata at pressure levels'
                rootgrp.featureType = "3_Dimension"
    
                #Arrange the format of dimensions for time, levels, latitude and longitude for dimension setup 
                LEV = lev[0][0]
                LAT = lat[0][0]
                LON = lon[0][0]
                #dimensions
                time  = rootgrp.createDimension('time', None)
                level = rootgrp.createDimension('level', len(LEV))
                lats   = rootgrp.createDimension('lats', len(LAT))
                lons   = rootgrp.createDimension('lons', len(LON))
                
                #Output the results of output variables
                for x in range(0,len(var_list)):
                    out_var = rootgrp.createVariable(var_list[x][0], 'f4', ('time','level','lats', 'lons'),fill_value=9.9999999E14)
                    out_var.standard_name = var_list[x][1]
                    out_var.long_name = var_list[x][2]
                    out_var.units         = var_list[x][3] 
                    out_var.missing_value = (9.9999999E14)
                    out_var.fmissing_value = (9.9999999E14, 'f')
                    out_var.vmin = (-9.9999999E14, 'f')   
                    out_var.vmax = (9.9999999E14, 'f')
                    out_var[:,:,:,:] = var_list[x][4][var_low:var_up,:,:,:]    #data generic name with data stored in it
    
                Time = rootgrp.createVariable('time', 'i4', ('time'))
                Time.standard_name = "time"
                # Time.units  = "hour since " + str(datetime.strptime(beg, '%Y/%m/%d'))
                Time.units  = "hours since 1980-1-1 00:00:0.0"                 
                Time.calendar = "gregorian"   
                # pass the values
                netCDFTime = []
                for x in range(0, len(time_ind1)):
                    netCDFTime.append(nc.date2num(time_ind1[x], units = Time.units, calendar = Time.calendar))
                Time[:] = netCDFTime[var_low:var_up] 
                                                                                                                                                                                                                                                                      
                Level = rootgrp.createVariable('level','i4', ('level'))
                Level.standard_name = "air_pressure"
                Level.long_name = "vertical level"
                Level.units = "hPa"
                Level.positive = "down"
                Level.axis = "Z"
                # pass the values
                netCDFLevel = []
                for x in range(0, len(lev[0][0])):
                    netCDFLevel.append(lev[0][0][x])
                Level[:] = netCDFLevel[:]                    

                Latitudes               = rootgrp.createVariable('latitude', 'f4',('lats'))
                Latitudes.standard_name = "latitude"
                Latitudes.units         = "degrees_north"
                Latitudes.axis          = "Y"
                Latitudes[:]  = lat[0][0][:]                                   

                Longitudes               = rootgrp.createVariable('longitude', 'f4',('lons'))
                Longitudes.standard_name = "longitude"
                Longitudes.units         = "degrees_east"
                Longitudes.axis          = "X"
                Longitudes[:] = lon[0][0][:]                                   
    
                #close the root group
                rootgrp.close()
          
class SaveNCDF_pl_3dmasm():                                                        
        """ write output netCDF file for abstracted variables from original meteorological data 
            at pressure levels
            demension: time, level, lat, lon
            variables: time: array([   0,  180,  360,  540,  720,  900, 1080, 1260], dtype=int32, Unit: minute)
                       relative humidity(time,lev,lat,lon), 
                       time, level, lat, lon.
            Args: 
            dir_data  = path.join(project_directory, "merra2") 
            date, time_ind2 = MERRAgeneric().getTime(beg, end)
            rh = MERRAgeneric().dataStuff_3d(position, id_lat, id_lon, out_variable_3dmasm)  
            lat, lon, lev, time = MERRAgeneric().latLon(out_variable_3dmasm, id_lat, id_lon) 
                     
        """
    
        def saveData(self, date, get_variables, id_lat, id_lon, id_lev, out_variable_3dmasm, chunk_size, time, lev, lat, lon, dir_data):
        # creat a NetCDF file for saving output variables (Dataset object, also the root group).
            """
            Args: 
            dir_data  = path.join(project_directory, "merra2")  
                               
            """
            # get time indices
            date_ind,time_ind1,time_ind2, time_ind3 = MERRAgeneric().getTime(date)
            
            #Setup size of saving file
            # chunk_size = 5
            date_size = len(date_ind)
            # for rh
            hour_size = len(time[0][0])
            int_size = date_size//chunk_size
            res_type = (date_size*hour_size)%(chunk_size*hour_size)
            
            if (res_type > 0):
                size_type = [chunk_size*hour_size]*int_size + [res_type]
            
            else:
                size_type = [chunk_size*hour_size]*int_size           

            #Get the wanted variables and Set up the list of output variables
            rh_total = []            
        
            var_out = {'RH':['relative_humidity', 'relative humidity','1', rh_total]}            
            
            var_list = []
            for i in range(0, len(get_variables[0:-4])):
                for x in var_out.keys():
                    if x == get_variables[i]:
                        print ("------Get Subset of Variable at Pressure Levels------", get_variables[i])
                        var = MERRAgeneric().dataStuff_3d(i, id_lat, id_lon, id_lev, out_variable_3dmasm)
                        # restructing the shape 
                        var_total = MERRAgeneric().restruDatastuff(var)
                        if x == 'RH':
                           rh_total = var_total
                           print "Conduct 1D Extrapolation for 'RH'"
                           var_total = MERRAgeneric().rhExtrapolate(rh_total)   #1D Extrapolation for Relative Humidity
                           rh_total = var_total
                        del var
                        var_out[x][3] = var_total
                        del var_total
                        var_list.append([get_variables[i],var_out[x][0], var_out[x][1], var_out[x][2], var_out[x][3]])

            # save nc file 
            var_low = 0
            var_up = 0
            for i in range(0, 1):
            # for i in range(0, len(size_type)):
                var = size_type[i]
                var_low = var_up
                var_up = var_low + var
                
                #set up file path and names 
                file_ncdf  = path.join(dir_data,("merra_pl-2" + "_" + (date_ind[var_low/len(time[0][0])]) + "_" + "to" + "_" +(date_ind[var_up/len(time[0][0]) - 1]) + ".nc"))      
                rootgrp = Dataset(file_ncdf, 'w', format='NETCDF4_CLASSIC')
                print("Saved File Type:",rootgrp.file_format)
                rootgrp.source      = 'Merra, abstrated meteorological variables from metadata at pressure levels'
                rootgrp.featureType = "3_Dimension"
    
                #Arrange the format of dimensions for time, levels, latitude and longitude for dimension setup 
                LEV = lev[0][0]
                LAT = lat[0][0]
                LON = lon[0][0]
                #dimensions
                time  = rootgrp.createDimension('time', None)
                level = rootgrp.createDimension('level', len(LEV))
                lats   = rootgrp.createDimension('lats', len(LAT))
                lons   = rootgrp.createDimension('lons', len(LON))
                
                #Output the results of output variables
                for x in range(0,len(var_list)):
                    out_var = rootgrp.createVariable(var_list[x][0], 'f4', ('time','level','lats','lons'),fill_value=9.9999999E14)
                    out_var[:,:,:,:] = var_list[x][4][var_low:var_up,:,:,:]       #data generic name with data stored in it      
                    out_var.standard_name = var_list[x][1]
                    out_var.long_name = var_list[x][2]
                    out_var.units         = var_list[x][3] 
                    out_var.missing_value = 9.9999999E14
                    out_var.fmissing_value = (9.9999999E14, 'f')
                    out_var.vmax = (9.9999999E14, 'f')
                    out_var.vmin = (-9.9999999E14, 'f')   
                
                Time = rootgrp.createVariable('time', 'i4', ('time'))
                Time.standard_name = "time"
                # Time.units = "hour since " + str(datetime.strptime(beg, '%Y/%m/%d'))
                Time.units  = "hours since 1980-01-01 00:00:0.0"                  
                Time.calendar = "gregorian"
                # pass the values
                netCDFTime = []
                for x in range(0, len(time_ind2)):
                    netCDFTime.append(nc.date2num(time_ind2[x], units = Time.units, calendar = Time.calendar))      
                Time[:] = netCDFTime[var_low:var_up]  
                                                                                                                                                                                                                               
                Level = rootgrp.createVariable('level','i4', ('level'))
                Level.standard_name = "air_pressure"
                Level.long_name = "vertical level"
                Level.units = "hPa"
                Level.positive = "down"
                Level.axis = "Z"
                # pass the values
                Level[:] = lev[0][0][:]                    

                Latitudes               = rootgrp.createVariable('latitude', 'f4',('lats'))
                Latitudes.standard_name = "latitude"
                Latitudes.units         = "degrees_north"
                Latitudes.axis          = 'Y'
                Latitudes[:]  = lat[0][0][:]                    # pass the values of latitude

                Longitudes               = rootgrp.createVariable('longitude', 'f4',('lons'))
                Longitudes.standard_name = "longitude"
                Longitudes.units         = "degrees_east"
                Longitudes.axis          = 'X'
                Longitudes[:] = lon[0][0][:]                    # pass the values of longitudes
    
                #close the root group
                rootgrp.close()
                          
            return rh_total

class MERRAsm():
    """Returns variables from downloaded MERRA 2d meteorological Diagnostics data, 
       which are abstracted with specific temporal and spatial range        
       
    Args:
        beg, end: A dictionary specifying the specific date desired as a datetime.datetime object.
              
        area: A dictionary delimiting the area to be queried with the latitudes
              north and south, and the longitudes west and east [decimal deg],to get 
              the indies of defined latitudes and longitudes.  
        
        variable:  List of variable(s) to download that can include one, several
                   , or all of these: ['T2M','U2M','V2M','U10M','V10M','lat','lon','time'].
                   T2M: 2-meter_air_temperature
                   U2M: 2-meter_eastward_wind
                   V2M: 2-meter_northward_wind
                   U10M: 10-meter_eastward_wind
                   V10M: 10-meter_northward_wind          
                      
     """
    def getDs(self, date, username, password, chunk_size):
        """Return the orginal datasets structured with defined chuncks form the specific MERRA-2 3d Analyzed Meteotological 
           Fields data products
           Args:
           username = ******
           password = ******
           urls = urls_2dm
           chunk_size = 5
           ds = MERRAgeneric().download(username, password, urls, chunk_size)
        """    
        urls_3dmana, urls_3dmasm, urls_2dm, urls_2ds, urls_2dr, url_2dc, urls_2dv = MERRAgeneric().getURLs(date)
        urls = urls_2dm
        ds = MERRAgeneric().download(username, password, urls, chunk_size)
        
        return ds

    
    def getVariables(self, get_variables, ds):
        """Return the objected variables from the specific MERRA-2 3D datasets        
            variable = ['T2M','U2M','V2M','U10M','V10M','lat','lon','time']
            ds = MERRAgeneric.download( username, password, urls_2dm, chunk_size)
            
        """
        out_variable_2dm = MERRAgeneric().Variables(get_variables, ds)

        return out_variable_2dm
         
    def getlatLon_2d(self, area, ds, out_variable_2dm, id_lat, id_lon):
        """
        Return the objected Latitude, Longitude, Levels, Time from specific MERRA-2 3D datasets
        Args:
            id_lat, id_lon =  MERRAgeneric().getArea(area, ds)
            out_variable_3dmana = MERRAgeneric().getVariables(variable, ds)
            p1 = -3 (id_Latitude)
            p2 = -2 (id_Longitude)
            p3 = -1 (id_Time) 

        """       
        
        id_lat, id_lon =  MERRAgeneric().getArea(area, ds)

        lat, lon, time = MERRAgeneric().latLon_2d(out_variable_2dm, id_lat, id_lon)
        
        return lat, lon, time
        

class MERRAsf():
    """Returns variables from downloaded MERRA 2d suface flux Diagnostics data, 
       which are abstracted with specific temporal and spatial range        
       
    Args:
        beg, end: A dictionary specifying the specific date desired as a datetime.datetime object.
              
        area: A dictionary delimiting the area to be queried with the latitudes
              north and south, and the longitudes west and east [decimal degree],to get 
              the indies of defined latitudes and longitudes.  
                      
        variable:  List of variable(s) to download that can include one, several
                   , or all of these: ['PRECTOT','lat','lon','time'].
              
    """
    
    def getDs(self, date, username, password, chunk_size):
        """Return the orginal datasets structured with defined chuncks form the specific MERRA-2 3d Analyzed Meteotological 
           Fields data products
           Args:
           username = ******
           password = ******
           urls = urls_2ds
           chunk_size = 5
           ds = MERRAgeneric().download(username, password, urls, chunk_size)
        """    
        
        urls_3dmana, urls_3dmasm, urls_2dm, urls_2ds, urls_2dr, url_2dc, urls_2dv = MERRAgeneric().getURLs(date)
        urls = urls_2ds
        ds = MERRAgeneric().download(username, password, urls, chunk_size)
        
        return ds
    
    def getVariables(self, get_variables, ds):
        """Return the objected variables from the specific MERRA-2 2D suface flux Diagnostics data    
           
           ds = MERRAgeneric.download( username, password, urls_2ds, chunk_size)
        """        
        
        out_variable_2ds = MERRAgeneric().Variables(get_variables, ds)

        return out_variable_2ds

    def getlatLon_2d(self, area, ds, out_variable_2ds, id_lat, id_lon):
        """
        Return the objected Latitude, Longitude, Levels, Time from specific MERRA-2 2D datasets
        Args:
            id_lat, id_lon =  MERRAgeneric().getArea(area, ds)
            out_variable_3dmana = MERRAgeneric().getVariables(variable, ds)
            p1 = -3 (id_Latitude)
            p2 = -2 (id_Longitude)
            p3 = -1 (id_Time) 

        """       

        id_lat, id_lon =  MERRAgeneric().getArea(area, ds)
        
        lat, lon, time = MERRAgeneric().latLon_2d(out_variable_2ds, id_lat, id_lon)
        
        return lat, lon, time


class MERRAsv():
    """Returns variables from downloaded MERRA 2d Single-Level, Assimilation,Single-Level Diagnostics data, 
        which are abstracted with specific temporal and spatial range        
        
    Args:
        beg, end: A dictionary specifying the specific date desired as a datetime.datetime object.
              
        area: A dictionary delimiting the area to be queried with the latitudes
              north and south, and the longitudes west and east [decimal degree],to get 
              the indies of defined latitudes and longitudes.  
                      
        variable:  List of variable(s) to download that can include one, several
                    , or all of these: ['T2MDEW','lat','lon','time'].
              
    """
    
    def getDs(self, date, username, password, chunk_size):
        """Return the orginal datasets structured with defined chuncks form the specific MERRA-2 2d Assimilation,Single-Level Diagnostics
            data products
            Args:
            username = ******
            password = ******
            urls = urls_2dv
            chunk_size = 5
            ds = MERRAgeneric().download(username, password, urls, chunk_size)
        """    
        
        urls_3dmana, urls_3dmasm, urls_2dm, urls_2ds, urls_2dr, url_2dc, urls_2dv = MERRAgeneric().getURLs(date)
        urls = urls_2dv
        ds = MERRAgeneric().download(username, password, urls, chunk_size)
        
        return ds
    
    def getVariables(self, get_variables, ds):
        """Return the objected variables from the specific MERRA-2 2d Assimilation Single-Level Diagnostics data data    
            
            ds = MERRAgeneric.download( username, password, urls_2ds, chunk_size)
        """        
        
        out_variable_2dv = MERRAgeneric().Variables(get_variables, ds)

        return out_variable_2dv

    def getlatLon_2d(self, area, ds, out_variable_2dv, id_lat, id_lon):
        """
        Return the objected Latitude, Longitude, Levels, Time from specific MERRA-2 2D datasets
        Args:
            id_lat, id_lon =  MERRAgeneric().getArea(area, ds)
            out_variable_3dmana = MERRAgeneric().getVariables(variable, ds)
            p1 = -3 (id_Latitude)
            p2 = -2 (id_Longitude)
            p3 = -1 (id_Time) 

        """       

        id_lat, id_lon =  MERRAgeneric().getArea(area, ds)
        
        lat, lon, time = MERRAgeneric().latLon_2d(out_variable_2dv, id_lat, id_lon)
        
        return lat, lon, time


class SaveNCDF_sa():                                  
        """ write output netCDF file for abstracted variables from original 2d meteorological Diagnostics dataset
        and suface flux Diagnostics datasets
            demension: time, lat, lon
            variables: time: array([   0,   60,  120,  180,  240,  300,  360,  420,  480,  540,  600,
                             660,  720,  780,  840,  900,  960, 1020, 1080, 1140, 1200, 1260,
                             1320, 1380], dtype=int32, Unit: minute)
                       t2m(time*lat*lon), 
                       u2m(time*lat*lon), 
                       v2m(time*lat*lon),
                       u10m(time*lat*lon)
                       v10m(time*lat*lon)
                       prectot(time*lat*lon), 
                       time, lat, lon.
            Args: 
            dir_data  = path.join(project_directory, "merra2")
            date, time_ind3 = MERRAgeneric().getTime(beg, end)
            t2m = dataStuff_2d(position, id_lat, id_lon, out_variable_2dm) 
            u2m = dataStuff_2d(position, id_lat, id_lon, out_variable_2dm)
            v2m = dataStuff_2d(position, id_lat, id_lon, out_variable_2dm)       
            u10m = dataStuff_2d(position,id_lat, id_lon, out_variable_2dm)        
            v10m = dataStuff_2d(position, id_lat, id_lon, out_variable_2dm) 
            prectot = dataStuff_2d(position, out_variable_2ds) 
            lat, lon,time = MERRAgeneric().latLon_2d(out_variable_2dm, id_lat, id_lon)
                     
        """
     
        def saveData(self, date, get_variables_2dm, get_variables_2ds, get_variables_2dv, id_lat, id_lon, out_variable_2dm, out_variable_2ds, out_variable_2dv, chunk_size, time, lat, lon, dir_data):
        # creat a NetCDF file for saving output variables (Dataset object, also the root group).
            """
            Args: 
            dir_data  = path.join(project_directory, "merra2") 
            """
            
            date_ind, time_ind1, time_ind2, time_ind3 = MERRAgeneric().getTime(date)
            
            #Setup size of saving file
            date_size = len(date_ind)
            hour_size = len(time[0][0])
            int_size = date_size//chunk_size
            res_type = (date_size*hour_size)%(chunk_size*hour_size)
                        
            if (res_type > 0):
                size_type = [chunk_size*hour_size]*int_size + [res_type]
            
            else:
                size_type = [chunk_size*hour_size]*int_size           

            #Get the wanted variables and set up the list for saving in netCDF file
            t2m_total = []
            u2m_total = []
            v2m_total = []
            u10m_total = []
            v10m_total = []
            prectot_total = []
            prectotcorr_total = []
            t2mdew_total = []
            
            var_out = {'T2M':['2-metre_air_temperature', 'temperature_at_2m_above_the_displacement_height','K', t2m_total],
                       'U2M':['2-metre_eastward_wind','eastward_wind_at _2m_above_the_displacement_height','m/s', u2m_total],
                       'V2M':['2-metre_northward_wind','northward_wind_at_2m_above_the_displacement_height','m/s', v2m_total],
                       'U10M':['10-metre_eastward_wind','eastward_wind_at_10m_above_displacement_height','m/s', u10m_total],
                       'V10M':['10-metre_northward_wind','northward_wind_at_10m_above_the_displacement_height', 'm/s', v10m_total],
                       'PRECTOT':['precipitation_flux','total_surface_precipitation_flux', 'kg/m2/s', prectot_total],
                       'PRECTOTCORR':['precipitation_flux','total_surface_precipitation_flux', 'kg/m2/s', prectotcorr_total],
                       'T2MDEW': ['2-metre_dew_point_temperature', 'dew_point_temperature_at_2_m' ,'K',  t2mdew_total]}
            
            
            var_list = []
            for i in range(0, len(get_variables_2dm[0:-3])):
                for x in var_out.keys():
                    if x == get_variables_2dm[i]:
                        print ("------Get Subset of Variable at Surface Level------", get_variables_2dm[i])
                        # the position of T2M, U2M, V2M, U10M, V10M in out_variable_2ds is the position in the get_variables
                        var = MERRAgeneric().dataStuff_2d(i, id_lat, id_lon, out_variable_2dm)   
                        # restructing the shape 
                        var_total = MERRAgeneric().restruDatastuff(var)
                        del var
                        var_out[x][3] = var_total
                        del var_total
                        var_list.append([get_variables_2dm[i], var_out[x][0], var_out[x][1], var_out[x][2], var_out[x][3]])

            for i in range(0, len(get_variables_2ds[0:-3])):
                for x in var_out.keys():
                    if x == get_variables_2ds[i]:
                        print ("------Get Subset of Variable at Surface Level------", get_variables_2ds[i])
                        # the position of PRECTOT in out_variable_2ds is 0
                        var = MERRAgeneric().dataStuff_2d(i, id_lat, id_lon, out_variable_2ds) 
                        # restructing the shape 
                        var_total = MERRAgeneric().restruDatastuff(var)
                        del var
                        var_out[x][3] = var_total
                        del var_total
                        var_list.append([get_variables_2ds[i], var_out[x][0], var_out[x][1], var_out[x][2], var_out[x][3]])

            for i in range(0, len(get_variables_2dv[0:-3])):
                for x in var_out.keys():
                    if x == get_variables_2dv[i]:
                        print ("------Get Subset of Variable at Surface Level------", get_variables_2dv[i])
                        # the position of PRECTOT in out_variable_2ds is 0
                        var = MERRAgeneric().dataStuff_2d(i, id_lat, id_lon, out_variable_2dv) 
                        # restructing the shape 
                        var_total = MERRAgeneric().restruDatastuff(var)
                        del var
                        var_out[x][3] = var_total
                        del var_total
                        var_list.append([get_variables_2dv[i], var_out[x][0], var_out[x][1], var_out[x][2], var_out[x][3]])
                        
            #save nc file
            var_low = 0
            var_up = 0
            for i in range(0, 1):
            # for i in range(0, len(size_type)):
                var = size_type[i]
                var_low = var_up
                var_up = var_low + var
    
                #set up file path and names 
                file_ncdf  = path.join(dir_data,("merra_sa" + "_" + (date_ind[var_low/len(time[0][0])]) + "_" + "to" + "_" +(date_ind[var_up/len(time[0][0]) - 1]) + ".nc"))
                rootgrp = Dataset(file_ncdf, 'w', format='NETCDF4_CLASSIC')
                print("Saved File Type:", rootgrp.file_format)
                rootgrp.source      = 'Merra, abstrated meteorological variables from metadata at surface level'
                rootgrp.featureType = "2_Dimension"
            
                #Arrange the format of dimensions for time, levels, latitude and longitude for dimension setup 
                LAT = lat[0][0]
                LON = lon[0][0]
                
                #dimensions
                time  = rootgrp.createDimension('time', None)
                lats   = rootgrp.createDimension('lats', len(LAT))
                lons   = rootgrp.createDimension('lons', len(LON))
                
                #Output the results of extracted variables
                for x in range(0,len(var_list)):
                    out_var = rootgrp.createVariable(var_list[x][0], 'f4', ('time','lats','lons'),fill_value=9.9999999E14)       
                    out_var.standard_name = var_list[x][1]
                    out_var.long_name = var_list[x][2]
                    out_var.units         = var_list[x][3] 
                    out_var.missing_value = 9.9999999E14
                    out_var.fmissing_value = (9.9999999E14, 'f')
                    out_var.vmax = (9.9999999E14, 'f')
                    out_var.vmin = (-9.9999999E14, 'f')   
                    out_var[:,:,:] = var_list[x][4][var_low:var_up,:,:]        #data generic name with data stored in it
        
                Time  = rootgrp.createVariable('time', 'i4', ('time'))
                Time.standard_name = "time"
                # Time.units         = "hour since " + str(datetime.strptime(beg, '%Y/%m/%d'))
                Time.units  = "hours since 1980-1-1 00:00:0.0" 
                Time.calendar      = "gregorian"
                # pass the values
                netCDFTime = []
                for x in range(0, len(time_ind3)):
                    netCDFTime.append(nc.date2num(time_ind3[x], units = Time.units, calendar = Time.calendar))
                Time[:] = netCDFTime[var_low:var_up]                                                                                                        
    
                Latitudes               = rootgrp.createVariable('latitude', 'f4',('lats'))
                Latitudes.standard_name = "latitude"
                Latitudes.units         = "degrees_north"
                Latitudes.axis          = "Y"
                Latitudes[:]  = lat[0][0][:]                    # pass the values of latitude
    
                Longitudes               = rootgrp.createVariable('longitude', 'f4',('lons'))
                Longitudes.standard_name = "longitude"
                Longitudes.units         = "degrees_east"
                Longitudes.axis          = "X"
                Longitudes[:] = lon[0][0][:]                    # pass the values of longitudes
            
            
                #close the root group
    
                rootgrp.close() 
                                  

class MERRAsr():
    """Returns variables from downloaded MERRA 2d radiation Diagnostics datasets, 
       which are abstracted with specific temporal and spatial range        
       
    Args:
        beg, end: A dictionary specifying the specific date desired as a datetime.datetime object.
              
        area: A dictionary delimiting the area to be queried with the latitudes
              north and south, and the longitudes west and east [decimal deg],to get 
              the indies of defined latitudes and longitudes.  
        
        variable:  List of variable(s) to download that can include one, several
                   , or all of these: ['SWGNT','LWGNT','SWGNTCLR','LWGNTCLR','SEGDN','SEGDNCLR','LWGAB','LWGABCLR','lat','lon','time'].
                   SWGNT:surface net downward shortwave flux(time*lat*lon)
                   LWGNT:surface net downward longwave flux(time*lat*lon)
                   SWGNTCLR:surface net downward shortwave flux assuming clear sky(time*lat*lon)
                   LWGNTCLR:surface net downward longwave flux assuming clear sky(time*lat*lon)
                   SWGDN: surface incoming shortwave flux(time*lat*lon)
                   LWGAB: surface absorbed longwave radiation(time*lat*lon)
                   SWGDNCLR: surface incoming shortwave flux assuming clear sky(time*lat*lon)
                   LWGABCLR: surface incoming longwave flux asusming clear sky(time*lat*lon)  
        
    """
    
    def getDs(self, date, username, password, chunk_size):
        """Return the orginal datasets structured with defined chuncks form the specific MERRA-2 2d radiation Diagnostics datasets 
           Args:
           username = ******
           password = ******
        """    
        urls_3dmana, urls_3dmasm, urls_2dm, urls_2ds, urls_2dr, url_2dc, urls_2dv = MERRAgeneric().getURLs(date)
        urls = urls_2dr
        ds = MERRAgeneric().download(username, password, urls, chunk_size)

        
        return ds

    
    def getVariables(self, get_variables, ds):
        """Return the objected variables from the specific MERRA-2 2D radiation Diagnostics datasets        
            get_variables = ['SWGNT','LWGNT', 'SWGNTCLR', 'LWGNTCLR','SWGDN','LWGAB', 'SWGDNCLR', 'LWGABCLR','lat','lon','time']
            urls = urls_2dr
            ds = MERRAgeneric.download( username, password, urls, chunk_size)   
        """
       
        out_variable_2dr = MERRAgeneric().Variables(get_variables, ds)

        return out_variable_2dr
         
    def getlatLon_2d(self, area, ds, out_variable_2dr, id_lat, id_lon):
        """
        Return the objected Latitude, Longitude, Time from specific MERRA-2 2D datasets
        Args:
            id_lat, id_lon =  MERRAgeneric().getArea(area, ds)
            out_variable_2dr = MERRAgeneric().getVariables(variable, ds)
            p1 = -3 (id_Latitude)
            p2 = -2 (id_Longitude)
            p3 = -1 (id_Time) 

        """       
        id_lat, id_lon =  MERRAgeneric().getArea(area, ds)

        lat, lon, time = MERRAgeneric().latLon_2d(out_variable_2dr, id_lat, id_lon)
        
        return lat, lon, time
        
class SaveNCDF_sr():                                  
        """ write output netCDF file for abstracted variables from original 2d radiation Diagnostics datasets  datasets 
            demension: time, lat, lon
            variables: time: array([   0,   60,  120,  180,  240,  300,  360,  420,  480,  540,  600,
                             660,  720,  780,  840,  900,  960, 1020, 1080, 1140, 1200, 1260,
                             1320, 1380], dtype=int32, Unit: minute)
                       swgdn(time,lat,lon),
                       swgdnclr(time,lat,lon),
                       lwgnt(time,lat,lon),
                       lwgem(time,lat,lon),
                       lwgntclr(time,lat,lon)
                       time, lat, lon.
            Args: 
            date, time_ind3 = MERRAgeneric().getTime(beg, end)
            swgdn = MERRAgeneric().dataStuff_2d(position, id_lat, id_lon, out_variable_2dr)
            swgdnclr = MERRAgeneric().dataStuff_2d(position, id_lat, id_lon, out_variable_2dr)
            lwgnt = MERRAgeneric().dataStuff_2d(position, id_lat, id_lon, out_variable_2dr)
            lwgem = MERRAgeneric().dataStuff_2d(position, id_lat, id_lon, out_variable_2dr)
            lwgntclr = MERRAgeneric().dataStuff_2d(position, id_lat, id_lon, out_variable_2dr)
            lwgab = MERRAgeneric().dataStuff_2d(position, id_lat, id_lon, out_variable_2dr)
            lat, lon, time = MERRAgeneric().latLon_2d(out_variable_2dr, id_lat, id_lon)
            
            Calculated:
            lwgdn = lwgnt + lwgem
            lwgdnclr = lwgntclr + lwgem    
                     
        """

        def saveData(self, date, get_variables, id_lat, id_lon, out_variable_2dr, chunk_size, time, lat, lon, dir_data):
        # creat a NetCDF file for saving output variables (Dataset object, also the root group).
            """
            Args: 
            dir_data  = path.join(project_directory, "merra2")  
            
            """
            date_ind, time_ind1, time_ind2, time_ind3 = MERRAgeneric().getTime(date)

            #Set up time_ind3 with the begin at year-mm-dd 00:30:00 
            time_ind3 = time_ind3 + timedelta(minutes=30)
            
            #Setup size of saving file
            date_size = len(date_ind)
            hour_size = len(time[0][0])
            int_size = date_size//chunk_size
            res_type = (date_size*hour_size)%(chunk_size*hour_size)
            
            if (res_type > 0):
                size_type = [chunk_size*hour_size]*int_size + [res_type]
            else:
                size_type = [chunk_size*hour_size]*int_size           

            #Get the wanted variables and Set up the list of output variables
    
            swgdn_total = []
            swgdnclr_total = []
            lwgnt_total = []
            lwgem_total = []
            lwgntclr_total = []
            lwgab_total = []
            lwgabclr_total= []
            
            var_out = {'SWGDN': ['surface_incoming_shortwave_flux', 'surface_incoming_shortwave_flux', 'W/m2', swgdn_total],
                       'SWGDNCLR': ['surface_incoming_shortwave_flux_assuming_clear_sky', 'surface_incoming_shortwave_flux_assuming_clear_sky', 'W/m2', swgdnclr_total],
                       'LWGNT':['surface_net_downward_longwave_flux','surface_net_downward_longwave_flux','W/m2', lwgnt_total],
                       'LWGEM': ['longwave_flux_emitted_from_surface','longwave_flux_emitted_from_surface', 'W/m2', lwgem_total],
                       'LWGNTCLR':['surface_net_downward_longwave_flux_assuming_clear_sky','surface_net_downward_longwave_flux_assuming_clear_sky', 'W/m2', lwgntclr_total],
                       'LWGAB': ['surface_absorbed_longwave_radiation', 'surface_absorbed_longwave_radiation', 'W/m2', lwgab_total],
                       'LWGABCLR': ['surface_abosrbed_longwave_radiation_assuming_clear_sky','surface_abosrbed_longwave_radiation_assuming_clear_sky', 'W/m2', lwgabclr_total]}
                       
            var_list = []
            for i in range(0, len(get_variables[0:-3])):
                for x in var_out.keys():
                    if x == get_variables[i]:
                        print ("------Get Subset of Variable at Surface Level------", get_variables[i])
                        var = MERRAgeneric().dataStuff_2d(i, id_lat, id_lon, out_variable_2dr)
                        # restructing the shape 
                        var_total = MERRAgeneric().restruDatastuff(var)
                        del var
                        var_out[x][3] = var_total
                        if x == 'LWGNT':
                            lwgnt_total = var_total
                        elif x == 'LWGNTCLR':
                            lwgntclr_total = var_total
                        elif x == 'LWGEM':
                            lwgem_total = var_total
                        elif x == 'LWGAB':  
                            lwgab_total = var_total
                        elif x == 'LWGABCLR':
                            lwgabclr_total = var_total      
                        del var_total
                        var_list.append([get_variables[i],var_out[x][0],var_out[x][1],var_out[x][2],var_out[x][3]])            
          
            # Getting downwelling longwave radiation flux conversed by the function below :
            # 
            # - downwelling longwave flux in air =  Upwelling longwave flux from surface + surface net downward longwave flux
            # - downwelling longwave flux in air assuming clear sky =  Upwelling longwave flux from surface + surface net downward longwave flux assuming clear sky
            
            
            lwgdn_total = lwgnt_total + lwgem_total
            lwgdnclr_total = lwgntclr_total + lwgem_total
                        
            #append LWGDN, LWGDNCLR     
            var_list.append(['LWGDN', 'downwelling_longwave_flux_in_air','downwelling_longwave_flux_in_air','W/m2', lwgdn_total])
            var_list.append(['LWGDNCLR','downwelling_longwave_flux_in_air_assuming_clear_sky','downwelling_longwave_flux_in_air_assuming_clear_sky','W/m2', lwgdnclr_total])
                        
            var_low = 0
            var_up = 0
            for i in range(0, 1):
            # for i in range(0, len(size_type)):
                var = size_type[i]
                var_low = var_up
                var_up = var_low + var
    
                # set up file path and names  
                file_ncdf  = path.join(dir_data,("merra_sr" + "_" + (date_ind[var_low/len(time[0][0])]) + "_" + "to" + "_" +(date_ind[var_up/len(time[0][0]) - 1]) + ".nc"))
                rootgrp = Dataset(file_ncdf, 'w', format='NETCDF4_CLASSIC')
                print("Saved File Type:", rootgrp.file_format)
                rootgrp.source      = 'Merra, abstrated radiation variables from metadata at surface level'
                rootgrp.featureType = "2_Dimension"
            
                #Arrange the format of dimensions for time, levels, latitude and longitude for dimension setup 
                LAT = lat[0][0]
                LON = lon[0][0]
    
                #dimensions
                time  = rootgrp.createDimension('time', None)
                lats   = rootgrp.createDimension('lats', len(LAT))
                lons   = rootgrp.createDimension('lons', len(LON))
            
                #Output the results of extracted variables
                for x in range(0,len(var_list)):
                    out_var = rootgrp.createVariable(var_list[x][0], 'f4', ('time','lats', 'lons'),fill_value=9.9999999E14)    
                    out_var.standard_name = var_list[x][1]
                    out_var.long_name = var_list[x][2]
                    out_var.units         = var_list[x][3] 
                    out_var.missing_value = 9.9999999E14
                    out_var.fmissing_value = (9.9999999E14, 'f')
                    out_var.vmax = (9.9999999E14, 'f')
                    out_var.vmin = (-9.9999999E14, 'f')   
                    out_var[:,:,:] = var_list[x][4][var_low:var_up,:,:]         
                                    
                Time               = rootgrp.createVariable('time', 'i4', ('time'))
                Time.standard_name = "time"
                # Time.units         = "hour since " + str(datetime.strptime(beg, '%Y/%m/%d'))
                Time.units  = "hours since 1980-1-1 00:30:0.0" 
                Time.calendar      = "gregorian"
                # pass the values
                netCDFTime = []
                for x in range(0, len(time_ind3)):
                    netCDFTime.append(nc.date2num(time_ind3[x], units = Time.units, calendar = Time.calendar))
                Time[:] = netCDFTime[var_low:var_up]                                                                                                        
    
                Latitudes               = rootgrp.createVariable('latitude', 'f4',('lats'))
                Latitudes.standard_name = "latitude"
                Latitudes.units         = "degrees_north"
                Latitudes.axis          = 'Y'
                Latitudes[:]  = lat[0][0][:]                    # pass the values of latitude
    
                Longitudes               = rootgrp.createVariable('longitude', 'f4',('lons'))
                Longitudes.standard_name = "longitude"
                Longitudes.units         = "degrees_east"
                Longitudes.axis          = 'X'
                Longitudes[:] = lon[0][0][:]                    # pass the values of longitudes
            
            
                #close the root group
                rootgrp.close()          

class MERRAsc():
    """Returns variables from downloaded MERRA 2d Constant model parameters, 
       which are abstracted with specific spatial range        
       
    Args:
        beg, end: A dictionary specifying the specific date desired as a datetime.datetime object.
              
        area: A dictionary delimiting the area to be queried with the latitudes
              north and south, and the longitudes west and east [decimal deg],to get 
              the indies of defined latitudes and longitudes.  
                      
        variable:  List of variable(s) to download that can include all of these: ['PHIS','FRLAKE','FRLAND','FRLANDICE','FROCEAN','SGH','lat','lon','time'].
              
    """
    
    def getDs(self, date, username, password, chunk_size):
        """Return the orginal datasets structured with defined chuncks form the specific MERRA-2 3d Analyzed Meteotological 
           Fields data products
           Args:
           username = ******
           password = ******
           urls = urls_2ds
           chunk_size = 5
           ds = MERRAgeneric().download(username, password, urls, chunk_size)
        """    
        
        urls_3dmana, urls_3dmasm, urls_2dm, urls_2ds, urls_2dr, url_2dc, urls_2dv = MERRAgeneric().getURLs(date)
        urls = url_2dc
        ds = MERRAgeneric().download(username, password, urls, chunk_size)
        
        return ds
    
    def getVariables(self, get_variables, ds):
        """Return the objected variables from the specific MERRA-2 2D constant model parameters    
           
           ds = MERRAgeneric.download( username, password, url_2dc, chunk_size)
        """        
        
        out_variable_2dc = MERRAgeneric().Variables(get_variables, ds)

        return out_variable_2dc

    def getlatLon_2d(self, area, ds, out_variable_2dc, id_lat, id_lon):
        """
        Return the objected Latitude, Longitude from specific MERRA-2 2D constant model parameters
        Args:
            id_lat, id_lon =  MERRAgeneric().getArea(area, ds)
            out_variable_2dc = MERRAgeneric().getVariables(variable, ds)
            p1 = -3 (id_Latitude)
            p2 = -2 (id_Longitude)
            p3 = -1 (id_Time) 

        """       

        id_lat, id_lon =  MERRAgeneric().getArea(area, ds)
        
        lat, lon, time = MERRAgeneric().latLon_2d(out_variable_2dc, id_lat, id_lon)
        
        return lat, lon, time

class SaveNCDF_sc():                                  
        """ write output netCDF file for abstracted variables from original 2d Constant Model Parameters
            demension: time, lat, lon
            variables: time: 1   
                       phis(time*lat*lon), 
                       frland(time*lat*lon),
                       time, lat, lon
            Args: 
            dir_data  = path.join(project_directory, "merra2") 
            phis = dataStuff_2d(position, out_variable_2dc)
            frland = dataStuff_2d(position, out_variable_2dc) 
            lat, lon, time = MERRAgeneric().latLon_2d(out_variable_2dc, id_lat, id_lon)
        """
     
        def saveData(self, get_variables_2dc, id_lat, id_lon, out_variable_2dc, chunk_size, time, lat, lon, dir_data):
        # creat a NetCDF file for saving output variables (Dataset object, also the root group).
            """
            Args: 
            dir_data  = path.join(project_directory, "merra2")
            """
            
            #Get the wanted variables and set up the list for saving in netCDF file
            phis_total = []
            frlake_total = []
            frland_total = []
            frlandice_total = []
            frocean_total = []
            sgh_total = []
            
            var_out = {'PHIS':['surface_geopotential_height', 'surface_geopotential_height','m2/s2', phis_total],
                       'FRLAKE':['fraction_of_lake','fraction_of_lake','1',frlake_total],
                       'FRLAND':['fraction_of_land','fraction_of_land', '1', frland_total],
                       'FRLANDICE':['fraction_of_land_ice', 'fraction_of_land_ice', '1', frlandice_total],
                       'FROCEAN':['fraction_of_ocean', 'fraction_of_ocean', '1',frocean_total],
                       'SGH':['isotropic_stdv_of_GWD_topography', 'isotropic_stdv_of_GWD_topography', 'm', sgh_total]}            
            
            var_list = []
            for i in range(0, len(get_variables_2dc[0:-3])):
                for x in var_out.keys():
                    if x == get_variables_2dc[i]:
                        print ("------Get Subset of Constant Model Paramters------", get_variables_2dc[i])
                        # the position of T2M, U2M, V2M, U10M, V10M in out_variable_2ds is the position in the get_variables
                        var = MERRAgeneric().dataStuff_2d(i, id_lat, id_lon, out_variable_2dc)   
                        # restructing the shape 
                        var_total = MERRAgeneric().restruDatastuff(var)
                        del var
                        var_out[x][3] = var_total
                        del var_total
                        var_list.append([get_variables_2dc[i], var_out[x][0], var_out[x][1], var_out[x][2], var_out[x][3]])

            #save netCDF file    
            #set up file path and names 
            file_ncdf  = path.join(dir_data,("merra_sc" + ".nc"))
            rootgrp = Dataset(file_ncdf, 'w', format='NETCDF4_CLASSIC')
            print("Saved File Type:", rootgrp.file_format)
            rootgrp.source      = 'Merra, abstrated constant model parameters'
            rootgrp.featureType = "2_Dimension"
        
            #Arrange the format of dimensions for time, levels, latitude and longitude for dimension setup 
            TIME = time[0][0]/60
            LAT = lat[0][0]
            LON = lon[0][0]
            
            #dimensions
            time  = rootgrp.createDimension('time', len(TIME))
            lats   = rootgrp.createDimension('lats', len(LAT))
            lons   = rootgrp.createDimension('lons', len(LON))
            
            #Output the results of extracted variables
            for x in range(0,len(var_list)):
                out_var = rootgrp.createVariable(var_list[x][0], 'f4', ('time','lats','lons'),fill_value=9.9999999E14)       
                out_var.standard_name = var_list[x][1]
                out_var.long_name = var_list[x][2]
                out_var.units         = var_list[x][3] 
                out_var.missing_value = 9.9999999E14
                out_var.fmissing_value = (9.9999999E14, 'f')
                out_var.vmax = (9.9999999E14, 'f')
                out_var.vmin = (-9.9999999E14, 'f')   
                out_var[:,:,:] = var_list[x][4][:,:,:]        #data generic name with data stored in it
    
            Time  = rootgrp.createVariable('time', 'i4', ('time'))
            Time.standard_name = "time"
            Time.units  = "hours since 1992-01-02 03:00:0.0" 
            Time.calendar      = "gregorian"
            #Set up the value of time (one single value)
            time_ind4 = datetime.combine(datetime.strptime("1992-01-02", "%Y-%m-%d") ,datetime.strptime("0300","%H%M").time())
            time_ind4 = (pandas.date_range(time_ind4, time_ind4, freq = '1H'))
            # pass the values
            netCDFTime = []
            for x in range(0, len(time_ind4)):
                 netCDFTime.append(nc.date2num(time_ind4[x], units = Time.units, calendar = Time.calendar))
            Time[:] = netCDFTime[:]                                                                                                        
                                                                                                  
            Latitudes               = rootgrp.createVariable('latitude', 'f4',('lats'))
            Latitudes.standard_name = "latitude"
            Latitudes.units         = "degrees_north"
            Latitudes.axis          = "Y"
            Latitudes[:]  = lat[0][0][:]                    # pass the values of latitude

            Longitudes               = rootgrp.createVariable('longitude', 'f4',('lons'))
            Longitudes.standard_name = "longitude"
            Longitudes.units         = "degrees_east"
            Longitudes.axis          = "X"
            Longitudes[:] = lon[0][0][:]                    # pass the values of longitudes
        
        
            #close the root group
            rootgrp.close()          
    

"""
Referenced from era_interim.py (Dr.Stephan Gruber): Class ERAdownload() 

Class for accessing the parameter file for downloading Merra-2 specified variables, latitude and longitude coordinates,
start, end date, minimum and maximum elevations.

Args:
    pfile: Full path to a Globsim Download Parameter file.
    

"""   
class MERRAdownload(object):
    """
    Class for MERRA-2 data that has methods for querying NASA GES DISC server, 
    and returning all variables usually wanted.
    
    Args:
        pfile: Full path to a Globsim Download Paramter file
        MERRAd = MERRAdownload(pfile)
        MERRAd.retrieve()

    Example:
        pfile = '/home/xquan/src/globsim/examples/par/examples.globsim_download'
        MERRAd = MERRAdownload(pfile)
        MERRAd.retrieve()   
    """
    def __init__(self, pfile):
        # read parameter file
        self.pfile = pfile
        par = ParameterIO(self.pfile)
        
        # assign bounding box
        self.area  = {'north':  par.bbN,
                      'south':  par.bbS,
                      'west' :  par.bbW,
                      'east' :  par.bbE}
                  
        # time bounds
        self.date  = {'beg' : par.beg,
                      'end' : par.end}

        # elevation
        self.elevation = {'min' : par.ele_min, 
                          'max' : par.ele_max}
        
        # data directory for MERRA-2  
        self.directory = path.join(par.project_directory, "merra2")  
        if path.isdir(self.directory) == False:
            raise ValueError("Directory does not exist: " + self.directory)   
        
        # credential 
        self.credential = path.join(par.credentials_directory, ".merrarc")
        self.account = open(self.credential, "r")
        self.inf = self.account.readlines()
        self.username = ''.join(self.inf[0].split())                                     # pass the first line to username  (covert list to str) 
        self.password = ''.join(self.inf[1].split())                                     # pass the second line to passworrd (covert list to str)
        
        # variables
        self.variables = par.variables
            
        # chunk size for downloading and storing data [days]        
        self.chunk_size = par.chunk_size
        
        # the diretory for storing downloaded data
        self.dir_data = self.directory
    
    def retrieve(self):
        """
        Retrive all required MERRA-2 data from NASA Goddard Earth Sciences Data and Information Services Center

        """                   
        
        # Get merra-2 3d meteorological analysis variables at pressure levels
                
        t_start = tc.time()
        
        #settings directory to store downloaded data 
        dir_data = self.dir_data
        
        #Account for Database Access
        username = self.username 
        password = self.password
        
        #Chunk size for spliting files and download [days], Format:Integer
        chunk_size = int(self.chunk_size)
        
        #Time slice Datetime Object
        date = self.date
                                                                                        
        # area bounding box [decimal degrees]
        area = self.area
        
        # Ground elevation range within area [m]
        elevation = self.elevation
        
        # Get merra-2 3d meteorological analysis variables at pressure levels
        
        startDay = date['beg']
        endDay   = date['end']
        
        # Get variables list in pfile from full list of variables
        
        variables = self.variables
        
        # build variables dictionaries between variables list in pfile and variables list from MERRA original datasets            
        full_variables_dic = {'air_temperature': ['air_temperature', '2-meter_air_temperature'],
                              'relative_humidity' : ['relative_humidity','2-metre_dewpoint_temperature'],
                              'precipitation_amount': ['precipitation_flux'],
                              'wind_from_direction':['eastward_wind','northward_wind','2-meter_eastward_wind','2-meter_northward_wind', '10-meter_eastward_wind', '10-meter_northward_wind'],
                              'wind_speed': ['eastward_wind','northward_wind','2-meter_eastward_wind','2-meter_northward_wind', '10-meter_eastward_wind', '10-meter_northward_wind'],
                              'downwelling_shortwave_flux_in_air': ['surface_incoming_shortwave_flux' ],
                              'downwelling_shortwave_flux_in_air_assuming_clear_sky': ['surface_incoming_shortwave_flux_assuming_clear_sky'],
                              'downwelling_longwave_flux_in_air': ['surface_net_downward_longwave_flux', 'longwave_flux_emitted_from_surface','surface_absorbed_longwave_radiation'],
                              'downwelling_longwave_flux_in_air_assuming_clear_sky': ['surface_net_downward_longwave_flux_assuming_clear_sky','longwave_flux_emitted_from_surface','surface_abosrbed_longwave_radiation_assuming_clear_sky']}
        
        # build variables Standards Names and referenced Names for downloading from orginal MERRA-2 datasets
        full_variables_pl_ana = {'geopotential_height':'H',
                                 'air_temperature':'T',
                                  'eastward_wind':'U',
                                  'northward_wind': 'V'}
        
        full_variables_pl_asm = {'relative_humidity': 'RH'}
        
        full_variables_sm = {'2-meter_air_temperature': 'T2M',
                             '2-meter_eastward_wind': 'U2M',
                             '2-meter_northward_wind':'V2M', 
                             '10-meter_eastward_wind':'U10M',
                             '10-meter_northward_wind':'V10M'}
        
        full_variables_sf = {'precipitation_flux': ['PRECTOT','PRECTOTCORR']}
        
        full_variables_sv = {'2-metre_dewpoint_temperature': 'T2MDEW'}
                        
        full_variables_sr = {'surface_incoming_shortwave_flux' : 'SWGDN',
                             'surface_incoming_shortwave_flux_assuming_clear_sky': 'SWGDNCLR',
                             'surface_net_downward_longwave_flux':'LWGNT',
                             'longwave_flux_emitted_from_surface': 'LWGEM',
                             'surface_net_downward_longwave_flux_assuming_clear_sky': 'LWGNTCLR',
                             'surface_absorbed_longwave_radiation': 'LWGAB',
                             'surface_abosrbed_longwave_radiation_assuming_clear_sky': 'LWGABCLR'}
                        
        x = 0
        for dt in rrule(DAILY, dtstart = startDay, until = endDay):
                currentDay = (str(dt.strftime("%Y")) + "/" + str(dt.strftime("%m")) + "/" + str(dt.strftime("%d")))
                x += 1
                if (x == 1):                                     
                    
                    date['beg'] = currentDay
                    
                    print 'DOWNLOADING BEGINS ON:', date['beg']
                    
                    #convert date['beg'] from string back to datetime object
                    date['beg'] = datetime.strptime(date['beg'],'%Y/%m/%d')  
            
                if (x == chunk_size or dt == endDay):   
                    
                    x = 0
                    date['end'] = currentDay
                    
                    print 'DOWNLOADING ENDS ON:', date['end']
                       
                    #convert date['beg'] from string back to datetime object
                    date['end'] = datetime.strptime(date['end'],'%Y/%m/%d')

                    # Get merra-2 3d meteorological assimilated variables at pressure levels
                    print ("-----Get Wanted Variables From Merra-2 3d, 3-hourly, Pressure-Level, Assimilated Meteorological Fields-----")
                    
                    # get the shared variables dictionaries and pass the information to the build-in dictionaries
                    get_variables = []
                    for i in range(0, len(variables)):
                        for var in full_variables_dic.keys():
                            if  var == variables[i]:
                                var_names = full_variables_dic[var]
                                #  Set up the variables list for accassing original MERRA-2 3d Assimilated Meteorological Fields dataset
                                for j in range(0, len(var_names)):
                                    for var1 in full_variables_pl_asm.keys():
                                        if var1 == var_names[j]:
                                            get_variables.append(full_variables_pl_asm[var1])
                    
                    get_variables = list(set(get_variables))                                                                
                    
                    # add the variables names of latitude, longitude, levels and time
                    get_variables.extend(['lat','lon','lev','time'])
                    
                    print get_variables
                    
                    ds_asm = MERRApl_asm().getDs(date, username, password, chunk_size)
                    
                    id_lat, id_lon =  MERRAgeneric().getArea(area, ds_asm)
                      
                    id_lev = MERRAgeneric().getPressureLevels(elevation)

                    out_variable_3dmasm = MERRApl_asm().getVariables(get_variables, ds_asm)
                    
                    lat, lon, lev, time = MERRApl_asm().getlatLon_3d(area, ds_asm, elevation, out_variable_3dmasm, id_lat, id_lon, id_lev)
                    
                    # Output meteorological assimilated variable at pressure levels
                    # For RH
                    rh_total = SaveNCDF_pl_3dmasm().saveData(date, get_variables, id_lat, id_lon, id_lev, out_variable_3dmasm, chunk_size, time, lev, lat, lon, dir_data)

                    print ("----------------------------------------Result NO.1: Completed----------------------------------------")
                      
                    #get merra-2 meterological varaibles at pressure levels
                    print ("-----Get Wanted Variables From Merra-2 3d, 6-hourly, Pressure-Level, Analyzed Meteorological Fields-----")
                    
                    # get the shared variables dictionaries and pass the information to the build-in dictionaries
                    get_variables = []
                    for i in range(0, len(variables)):
                        for var in full_variables_dic.keys():
                            if  var == variables[i]:
                                var_names = full_variables_dic[var]
                                #  Set up the variables list for accassing original MERRA-2 3d Analyzed Meteorological Fields dataset
                                for j in range(0, len(var_names)):
                                    for var1 in full_variables_pl_ana.keys():
                                        if var1 == var_names[j]:
                                            get_variables.append(full_variables_pl_ana[var1])
                    get_variables = list(set(get_variables))                                            
                   
                    # !ADD Geopotential Height in the first element of downloading list.Must be the first one
                    get_variables.insert(0,'H')
                     # add the variables names of geopotental height, latitude, longitude, levels and time
                    get_variables.extend(['lat','lon','lev','time'])
                      
                    print get_variables
                      
                    ds_ana = MERRApl_ana().getDs(date, username, password, chunk_size)
                      
                    id_lat, id_lon =  MERRAgeneric().getArea(area, ds_ana)
                      
                    id_lev = MERRAgeneric().getPressureLevels(elevation)
                      
                    out_variable_3dmana = MERRApl_ana().getVariables(get_variables, ds_ana)
                      
                    lat, lon, lev, time = MERRApl_ana().getlatLon_3d(area, ds_ana, elevation, out_variable_3dmana, id_lat, id_lon, id_lev)
                      
                    # Output merra-2 meteorological analysis variable at pressure levels
                    #For T, V, U, H
                      
                    SaveNCDF_pl_3dmana().saveData(date, get_variables, id_lat, id_lon, id_lev, out_variable_3dmana, chunk_size, time, lev, lat, lon, dir_data, rh_total, elevation)
                                            
                    print ("----------------------------------------Result NO.2: Completed----------------------------------------")
        
                    # Get merra-2 2d meteorological Diagnostics variables at surface level
                    print ("-----Get Wanted Variables From Merra-2 2d, 1-hourly, Single-level, Meteorological Diagnostics-----")
                    
                    # get the shared variables dictionaries and pass the information to the build-in dictionaries
                    get_variables = []
                    for i in range(0, len(variables)):
                        for var in full_variables_dic.keys():
                            if  var == variables[i]:
                                var_names = full_variables_dic[var]
                                #  Set up the variables list for accassing original MERRA-2 2d Meteorological Diagnostics dataset
                                for j in range(0, len(var_names)):
                                    for var1 in full_variables_sm.keys():
                                        if var1 == var_names[j]:
                                            get_variables.append(full_variables_sm[var1])
                    get_variables = list(set(get_variables))                                            
                    # add the variables names of latitude, longitude and time
                    get_variables.extend(['lat','lon','time'])
                    
                    print get_variables
                    
                    ds_2dm = MERRAsm().getDs(date, username, password, chunk_size)
                    
                    out_variable_2dm = MERRAsm().getVariables(get_variables, ds_2dm)
        
                    lat, lon, time = MERRAsm().getlatLon_2d(area, ds_2dm, out_variable_2dm, id_lat, id_lon)
                    
                    get_variables_2dm = get_variables
                                     
                    # Get merra-2 2d suface flux Diagnostics variables at surface level
                    print ("-----Get Wanted Variables From Merra-2 2d, 1-hourly, Single-level, Surface Flux Diagnostics-----")
                    
                    # get the shared variables dictionaries and pass the information to the build-in dictionaries
                    get_variables = []
                    for i in range(0, len(variables)):
                        for var in full_variables_dic.keys():
                            if  var == variables[i]:
                                var_names = full_variables_dic[var]
                                #  Set up the variables list for accassing original MERRA-2 2d Surface Flux Diagnostics dataset
                                for j in range(0, len(var_names)):
                                    for var1 in full_variables_sf.keys():
                                        if var1 == var_names[j]:
                                            get_variables.append(full_variables_sf[var1])
                    get_variables = list(itertools.chain(*get_variables))
                    get_variables = list(set(get_variables))                                          
                    # add the variables names of latitude, longitude and time
                    get_variables.extend(['lat','lon','time'])

                    print get_variables                   
                    
                    ds_2ds = MERRAsf().getDs(date, username, password, chunk_size)
        
                    out_variable_2ds = MERRAsf().getVariables(get_variables, ds_2ds)
                    
                    lat, lon, time = MERRAsf().getlatLon_2d(area, ds_2ds, out_variable_2ds, id_lat, id_lon)
                    
                    get_variables_2ds = get_variables               
                    
                    print ("-----Get Wanted Variables From Merra-2 2d, 1-hourly, Single-Level,Assimilation,Single-Level Diagnostics-----")
                    
                    # get the shared variables dictionaries and pass the information to the build-in dictionaries
                    get_variables = []
                    for i in range(0, len(variables)):
                        for var in full_variables_dic.keys():
                            if  var == variables[i]:
                                var_names = full_variables_dic[var]
                                #  Set up the variables list for accassing original MERRA-2 2d Assimilation Single Level Diagnostics dataset
                                for j in range(0, len(var_names)):
                                    for var1 in full_variables_sv.keys():
                                        if var1 == var_names[j]:
                                            get_variables.append(full_variables_sv[var1])
                    get_variables = list(set(get_variables))                                          
                    # add the variables names of latitude, longitude and time
                    get_variables.extend(['lat','lon','time'])

                    print get_variables                   
                    
                    ds_2dv = MERRAsv().getDs(date, username, password, chunk_size)
        
                    out_variable_2dv = MERRAsv().getVariables(get_variables, ds_2dv)
                    
                    lat, lon, time = MERRAsv().getlatLon_2d(area, ds_2dv, out_variable_2dv, id_lat, id_lon)
                    
                    get_variables_2dv = get_variables                                    
                                       
                    # Output marra-2 variable at surface level 
                    SaveNCDF_sa().saveData(date,  get_variables_2dm, get_variables_2ds, get_variables_2dv, id_lat, id_lon, out_variable_2dm, out_variable_2ds, out_variable_2dv, chunk_size, time, lat, lon, dir_data)
                    
                    print ("----------------------------------------Result NO.3: Completed----------------------------------------")
        
                    # Get merra-2 2d radiation variables
                    print ("-----Get Wanted Variables From Merra-2 2d, 1-Hourly, Single-Level, Radiation Diagnostics-----")
                    
                     # get the shared variables dictionaries and pass the information to the build-in dictionaries
                    get_variables = []
                    for i in range(0, len(variables)):
                        for var in full_variables_dic.keys():
                            if  var == variables[i]:
                                var_names = full_variables_dic[var]
                                #  Set up the variables list for accassing original MERRA-2 2d Radiation Diagnostics dataset
                                for j in range(0, len(var_names)):
                                    for var1 in full_variables_sr.keys():
                                        if var1 == var_names[j]:
                                            get_variables.append(full_variables_sr[var1])
                    get_variables = list(set(get_variables))                                            
                    # add the variables names of latitude, longitude and time
                    get_variables.extend(['lat','lon','time'])
                    
                    print get_variables
                    
                    ds_2dr = MERRAsr().getDs(date, username, password, chunk_size)
        
                    out_variable_2dr = MERRAsr().getVariables(get_variables, ds_2dr)
        
                    lat, lon, time = MERRAsr().getlatLon_2d(area, ds_2dr, out_variable_2dr, id_lat, id_lon)
        
                    #Output merra-2 radiation variables 
                    SaveNCDF_sr().saveData(date, get_variables, id_lat, id_lon, out_variable_2dr, chunk_size, time, lat, lon, dir_data)
                    
                    print ("----------------------------------------Result NO.4: Completed----------------------------------------")
        
        # Get merra-2 2d Constant Model Parameters (being outside of time & date looping!!)
        print ("-----Get Wanted Variables From Merra-2 2d, Time-Invariant, Single-level, Constant Model Parameters-----")
        
        # get the shared variables dictionaries and pass the information to the build-in dictionaries
        get_variables_2dc = ['PHIS','FRLAKE','FRLAND','FRLANDICE','FROCEAN','SGH','lat','lon','time']
        
        print get_variables_2dc                   
        
        ds_2dc = MERRAsc().getDs(date, username, password, chunk_size)
    
        out_variable_2dc = MERRAsc().getVariables(get_variables_2dc, ds_2dc)
        
        lat, lon, time = MERRAsc().getlatLon_2d(area, ds_2dc, out_variable_2dc, id_lat, id_lon)
                         
        # Output marra-2 variable at surface level 
        SaveNCDF_sc().saveData(get_variables_2dc, id_lat, id_lon, out_variable_2dc, chunk_size, time, lat, lon, dir_data)
        
        print ("----------------------------------------Result NO.5: Completed----------------------------------------")
   
        t_end = tc.time()
        t_total = int((t_end - t_start)/60)
        print ("Total Time (Minutes):", t_total)
           

class MERRAinterpolate(object):
    """
    Algorithms to interpolate MERRA-2 netCDF files to station coordinates. 
    All variables retains their original units and time-steps. 
    
    Referenced from era_interim.py (Dr.Stephan Gruber): Class ERAinterpolate()     
    
    Args:
        ifile: Full path to a Globsim Interpolate Paramter file
        MERRAd = MERRAinterpolate(ifile)


    Example:
        ifile = '/home/xquan/src/globsim/examples/par/examples.globsim_interpolate'
        MERRAinterpolate(ifile)
      
    """

    def __init__(self, ifile):
        #read parameter file
        self.ifile = ifile
        par = ParameterIO(self.ifile)
        self.dir_inp = path.join(par.project_directory,'merra2') 
        self.dir_out = path.join(par.project_directory,'station')
        self.variables = par.variables
        self.list_name = par.list_name
        self.stations_csv = path.join(par.project_directory,
                                      'par', par.station_list)
        
        #read station points 
        self.stations = StationListRead(self.stations_csv)  
        
        # time bounds, add one day to par.end to include entire last day
        self.date  = {'beg' : par.beg,
                      'end' : par.end + timedelta(days=1)}
        
        # chunk size: how many time steps to interpolate at the same time?
        # A small chunk size keeps memory usage down but is slow.
        self.cs  = int(par.chunk_size)
                                    
                                    
    def MERRA2interp2D(self, ncfile_in, ncf_in, points, tmask_chunk,
                       variables=None, date=None):    
        """
        Biliner interpolation from fields on regular grid (latitude, longitude) 
        to individual point stations (latitude, longitude). This works for
        surface and for pressure level files (all MERRA-2 files).
          
        Args:
            ncfile_in: Full path to an MERRA-2 derived netCDF file. This can
                        contain wildcards to point to multiple files if temporal
                        chunking was used.
              
            ncf_in: A netCDF4.MFDataset derived from reading in MERRA-2 multiple files (def MERRA2station_append())
            
            points: A dictionary of locations. See method StationListRead in
                    generic.py for more details.
        
            variables:  List of variable(s) to interpolate such as 
                        ['T','RH','U','V',' T2M', 'U2M', 'V2M', 'U10M', 'V10M', 'PRECTOT', 'SWGDN','SWGDNCLR','LWGDN', 'LWGDNCLR'].
                        Defaults to using all variables available.
        
            date: Directory to specify begin and end time for the derived time 
                  series. Defaluts to using all times available in ncfile_in.
              
        Example:
            from datetime import datetime
            date  = {'beg' : datetime(2008, 1, 1),
                      'end' : datetime(2008,12,31)}
            variables  = ['T','U', 'V']       
            stations = StationListRead("points.csv")      
            MERRA2station('merra_sa.nc', 'merra_sa_inter.nc', stations, 
                        variables=variables, date=date)        
        """   

        # is it a file with pressure levels?
        pl = 'level' in ncf_in.dimensions.keys()

        # get spatial dimensions
        lat  = ncf_in.variables['latitude'][:]
        lon  = ncf_in.variables['longitude'][:]
        if pl: # only for pressure level files
            lev  = ncf_in.variables['level'][:]
            nlev = len(lev)
              
        # test if time steps to interpolate remain
        nt = sum(tmask_chunk)
        if nt == 0:
            raise ValueError('No time steps from netCDF file selected.')
    
        # get variables
        varlist = [x.encode('UTF8') for x in ncf_in.variables.keys()]
        varlist.remove('time')
        varlist.remove('latitude')
        varlist.remove('longitude')
        if pl: #only for pressure level files
            varlist.remove('level')
            
        # remove extra variables from merra2 
        varlist = MERRAgeneric().MERRA_skip(varlist)  
    
        #list variables that should be interpolated
        if variables is None:
            variables = varlist
        #test is variables given are available in file
        if (set(variables) < set(varlist) == 0):
            raise ValueError('One or more variables not in netCDF file.')
       
        # Create source grid from a SCRIP formatted file. As ESMF needs one
        # file rather than an MFDataset, give first file in directory.
        ncsingle = filter(listdir(self.dir_inp), path.basename(ncfile_in))[0]
        ncsingle = path.join(self.dir_inp, ncsingle)
        sgrid = ESMF.Grid(filename=ncsingle, filetype=ESMF.FileFormat.GRIDSPEC)

        # create source field on source grid
        if pl: #only for pressure level files
            sfield = ESMF.Field(sgrid, name='sgrid',
                                staggerloc=ESMF.StaggerLoc.CENTER,
                                ndbounds=[len(variables), nt, nlev])
        else: # 2D files
            sfield = ESMF.Field(sgrid, name='sgrid',
                                staggerloc=ESMF.StaggerLoc.CENTER,
                                ndbounds=[len(variables), nt])

        # assign data from ncdf: (variable, time, latitude, longitude) 
        for n, var in enumerate(variables):
            if pl: # only for pressure level files
                sfield.data[n,:,:,:,:] = ncf_in.variables[var][tmask_chunk,:,:,:].transpose((0,1,3,2)) 
            else:
                sfield.data[n,:,:,:] = ncf_in.variables[var][tmask_chunk,:,:].transpose((0,2,1))

        # create locstream, CANNOT have third dimension!!!
        locstream = ESMF.LocStream(len(self.stations), coord_sys=ESMF.CoordSys.SPH_DEG)
        locstream["ESMF:Lon"] = list(self.stations['longitude_dd'])
        locstream["ESMF:Lat"] = list(self.stations['latitude_dd'])

        # create destination field
        if pl: # only for pressure level files
            dfield = ESMF.Field(locstream, name='dfield', 
                                ndbounds=[len(variables), nt, nlev])
        else:
            dfield = ESMF.Field(locstream, name='dfield', 
                                ndbounds=[len(variables), nt])    

        # regridding function, consider ESMF.UnmappedAction.ERROR
        regrid2D = ESMF.Regrid(sfield, dfield,
                                regrid_method=ESMF.RegridMethod.BILINEAR,
                                unmapped_action=ESMF.UnmappedAction.IGNORE,
                                dst_mask_values=None)
                  
        # regrid operation, create destination field (variables, times, points)
        dfield = regrid2D(sfield, dfield)        
        sfield.destroy() #free memory                  
		            
        return dfield, variables

    def MERRA2station(self, ncfile_in, ncfile_out, points,
                             variables = None, date = None):
        
        """
        Given the type of variables to interpoalted from MERRA2 downloaded diretory
        Create the empty of netCDF file to hold the interpolated results, by calling MERRAgeneric().netCDF_empty
        Get the interpolated results from MERRA2station
        Append all variables into the empty netCDF file
        Close all files
        
        Args:
        ncfile_in: Full path to an MERRA-2 derived netCDF file. This can
                    contain wildcards to point to multiple files if temporal
                    chunking was used.
            
        ncfile_out: Full path to the output netCDF file to write.     
        
        points: A dictionary of locations. See method StationListRead in
                generic.py for more details.
    
        variables:  List of variable(s) to interpolate such as 
                    ['T','RH','U','V',' T2M', 'U2M', 'V2M', 'U10M', 'V10M', 'PRECTOT', 'SWGDN','SWGDNCLR','LWGDN', 'LWGDNCLR'].
                    Defaults to using all variables available.
    
        date: Directory to specify begin and end time for the derived time 
                series. Defaluts to using all times available in ncfile_in.
  
        """
        
        # read in one type of mutiple netcdf files
        ncf_in = nc.MFDataset(ncfile_in, 'r', aggdim ='time')
        
        # is it a file with pressure levels?
        pl = 'level' in ncf_in.dimensions.keys()

        # build the output of empty netCDF file
        MERRAgeneric().netCDF_empty(ncfile_out, self.stations, ncf_in) 
                                     
        # open the output netCDF file, set it to be appendable ('a')
        ncf_out = nc.Dataset(ncfile_out, 'a')

        # get time and convert to datetime object
        nctime = ncf_in.variables['time'][:]
        #"hours since 1980-01-01 00:00:0.0"
        t_unit = ncf_in.variables['time'].units 
        try :
            t_cal = ncf_in.variables['time'].calendar
        except AttributeError : # Attribute doesn't exist
            t_cal = u"gregorian" # or standard
        time = nc.num2date(nctime, units = t_unit, calendar = t_cal)
                                                                                    
        # detect invariant files (topography etc.)
        if len(time) ==1:
            invariant=True
        else:
            invariant=False                                                                         
        
        # restrict to date/time range if given
        if date is None:
            tmask = time < datetime(3000, 1, 1)
        else:
            tmask = (time <= date['end']) * (time >= date['beg'])
                              
        # get time indices
        time_in = nctime[tmask]

        # ensure that chunk sizes cover entire period even if
        # len(time_in) is not an integer multiple of cs
        niter  = len(time_in)/self.cs
        niter += ((len(time_in) % self.cs) > 0)

        # loop in chunk size cs
        for n in range(niter):
            #indices
            beg = n * self.cs
            #restrict last chunk to lenght of tmask plus one (to get last time)
            end = min(n*self.cs + self.cs, len(time_in))
            
            #time to make tmask for chunk 
            beg_time = nc.num2date(nctime[beg], units = t_unit, calendar = t_cal)
            if invariant:
                # allow topography to work in same code, len(nctime) = 1
                end_time = nc.num2date(nctime[0], units=t_unit, calendar=t_cal)
            else:
                end_time = nc.num2date(nctime[end], units=t_unit, calendar=t_cal)
            
            # !! CAN'T HAVE '<= end_time', would damage appeding 
	    tmask_chunk = (time < end_time) * (time >= beg_time)
	    if invariant:
                # allow topography to work in same code
                tmask_chunk = [True]
           
	    # get the interpolated variables
            dfield, variables = self.MERRA2interp2D(ncfile_in, ncf_in, self.stations, tmask_chunk,
                                    variables=None, date=None) 

            # append time
            ncf_out.variables['time'][:] = np.append(ncf_out.variables['time'][:], 
                                                     time_in[beg:end])
            #append variables
            for i, var in enumerate(variables):
                if variables_skip(var):
                    continue
                                          
                # extra treatment for pressure level files
                try:
                    lev = ncf_in.variables['level'][:]
                    # dimension: time, level, latitude, longitude
                    ncf_out.variables[var][beg:end,:,:] = dfield.data[i,:,:,:]    		    
                except:
                    # time, latitude, longitude
                    ncf_out.variables[var][beg:end,:] = dfield.data[i,:,:]		    
                                     
        #close the file
        ncf_in.close()
        ncf_out.close()         
        #close read-in and read-out files====================================                  
        
    def levels2elevation(self, ncfile_in, ncfile_out):    
        """
        Linear 1D interpolation of pressure level data available for individual
        stations to station elevation. Where and when stations are below the 
        lowest pressure level, they are assigned the value of the lowest 
        pressure level.
        
        """
        # open file 
        ncf = nc.MFDataset(ncfile_in, 'r', aggdim='time')
        height = ncf.variables['height'][:]
        nt = len(ncf.variables['time'][:])
        nl = len(ncf.variables['level'][:])
        
        # list variables
        varlist = [x.encode('UTF8') for x in ncf.variables.keys()]
        varlist.remove('time')
        varlist.remove('station')
        varlist.remove('latitude')
        varlist.remove('longitude')
        varlist.remove('level')
        varlist.remove('height')
        varlist.remove('H')

        # === open and prepare output netCDF file ==============================
        # dimensions: station, time
        # variables: latitude(station), longitude(station), elevation(station)
        #            others: ...(time, station)
        # stations are integer numbers
        # create a file (Dataset object, also the root group).
        rootgrp = nc.Dataset(ncfile_out, 'w', format='NETCDF4')
        rootgrp.Conventions = 'CF-1.6'
        rootgrp.source      = 'MERRA-2, interpolated (bi)linearly to stations'
        rootgrp.featureType = "timeSeries"

        # dimensions
        station = rootgrp.createDimension('station', len(height))
        time    = rootgrp.createDimension('time', nt)

        # base variables
        time           = rootgrp.createVariable('time',     'i4',('time'))
        time.long_name = 'time'
        time.units     = 'hours since 1980-01-01 00:00:0.0'
        time.calendar  = 'gregorian'
        station             = rootgrp.createVariable('station',  'i4',('station'))
        station.long_name   = 'station for time series data'
        station.units       = '1'
        latitude            = rootgrp.createVariable('latitude', 'f4',('station'))
        latitude.long_name  = 'latitude'
        latitude.units      = 'degrees_north'    
        longitude           = rootgrp.createVariable('longitude','f4',('station'))
        longitude.long_name = 'longitude'
        longitude.units     = 'degrees_east'  
        height           = rootgrp.createVariable('height','f4',('station'))
        height.long_name = 'height_above_reference_ellipsoid'
        height.units     = 'm'  
       
        # assign base variables
        time[:] = ncf.variables['time'][:]
        station[:]   = ncf.variables['station'][:]
        latitude[:]  = ncf.variables['latitude'][:]
        longitude[:] = ncf.variables['longitude'][:]
        height[:]    = ncf.variables['height'][:]
        
        # create and assign variables from input file
        for var in varlist:
            tmp   = rootgrp.createVariable(var,'f4',('time', 'station'))    
            tmp.long_name = ncf.variables[var].long_name.encode('UTF8')
            tmp.units     = ncf.variables[var].units.encode('UTF8')
        
        # add air pressure as new variable
        var = 'air_pressure'
        varlist.append(var)
        tmp   = rootgrp.createVariable(var,'f4',('time', 'station'))    
        tmp.long_name = var.encode('UTF8')
        tmp.units     = 'hPa'.encode('UTF8')            
        # end file prepation ===================================================
                                                                                             
        # loop over stations
        for n, h in enumerate(height): 
            # geopotential unit: height [m]
            # shape: (time, level)
            ele = ncf.variables['H'][:,:,n]
            # TODO: check if height of stations in data range (+50m at top, lapse r.)
            
            # difference in elevation. 
            # level directly above will be >= 0
            dele = -(ele - h)
            # vector of level indices that fall directly above station. 
            # Apply after ravel() of data.
            va = np.argmin(dele + (dele < 0) * 100000, axis=1) 
            # mask for situations where station is below lowest level
            mask = va < (nl-1)
            va += np.arange(ele.shape[0]) * ele.shape[1]
            
            # Vector level indices that fall directly below station.
            # Apply after ravel() of data.
            vb = va + mask # +1 when OK, +0 when below lowest level
            
            # weights
            wa = np.absolute(dele.ravel()[vb]) 
            wb = np.absolute(dele.ravel()[va])
            wt = wa + wb
            wa /= wt # Apply after ravel() of data.
            wb /= wt # Apply after ravel() of data.
            
            #loop over variables and apply interpolation weights
            for v, var in enumerate(varlist):
                if var == 'air_pressure':
                    # pressure [hPa] variable from levels, shape: (time, level)
                    data = np.repeat([ncf.variables['level'][:]],
                                      len(time),axis=0).ravel()
		    ipol = data[va]*wa + data[vb]*wb   # interpolated value
		    #---------------------------------------------------------
		    #if mask[pixel] == false, pass the maximum of pressure level to pixles
		    level_highest = ncf.variables['level'][:][-1]
		    level_lowest = ncf.variables['level'][:][0]
		    for j, value in enumerate(ipol):
		        if value == level_highest:
			    ipol[j] = level_lowest
	            #---------------------------------------------------------	    	    				                     
                else:    
                    #read data from netCDF
                    data = ncf.variables[var][:,:,n].ravel()
                    ipol = data[va]*wa + data[vb]*wb   # interpolated value                    
                rootgrp.variables[var][:,n] = ipol # assign to file   
    
        rootgrp.close()
        ncf.close()
        # closed file ==========================================================    

    def TranslateCF2short(self, dpar):
        """
        Map CF Standard Names into short codes used in ERA-Interim netCDF files.
        """
        varlist = [] 
        for var in self.variables:
            varlist.append(dpar.get(var))
        # drop none
        varlist = [item for item in varlist if item is not None]      
        # flatten
        varlist = [item for sublist in varlist for item in sublist]         
        return(varlist) 

    def process(self):
        """
        Interpolate point time series from downloaded data. Provides access to 
        the more generically MERRA-like interpolation functions.
        """                       

        # 2D Interpolation for Constant Model Parameters    
        # dictionary to translate CF Standard Names into MERRA
        # pressure level variable keys.            
        dummy_date  = {'beg' : datetime(1992, 1, 2, 3, 0),
                        'end' : datetime(1992, 1, 2, 3, 0)}        
        self.MERRA2station(path.join(self.dir_inp,'merra_sc.nc'), 
                          path.join(self.dir_out,'merra_sc_' + 
                                    self.list_name + '.nc'), self.stations,
                                    ['PHIS','FRLAND','FROCEAN', 'FRLANDICE','FRLAKE'], date = dummy_date)      

        # === 2D Interpolation for Surface Analysis Data ===    
        # dictionary to translate CF Standard Names into MERRA2
        # pressure level variable keys. 
        dpar = {'air_temperature'   : ['T2M', 'T2MDEW'],  # [K] 2m values
                'precipitation_amount' : ['PRECTOTCORR'],  # [kg/m2/s] total precipitation                                                            
                'wind_speed' : ['U2M', 'V2M', 'U10M','V10M']}   # [m s-1] 2m & 10m values   
        varlist = self.TranslateCF2short(dpar)                      
        self.MERRA2station(path.join(self.dir_inp,'merra_sa_*.nc'), 
                           path.join(self.dir_out,'merra_sa_' + 
                                     self.list_name + '.nc'), self.stations,
                                     varlist, date = self.date)          
        
        # 2D Interpolation for Single-level Radiation Diagnostics Data 'SWGDN', 'LWGDN', 'SWGDNCLR'. 'LWGDNCLR' 
        # dictionary to translate CF Standard Names into MERRA2
        # pressure level variable keys.       
        dpar = {'downwelling_shortwave_flux_in_air' : ['SWGDN'], # [W/m2] short-wave downward
                'downwelling_longwave_flux_in_air'  : ['LWGDN'], # [W/m2] long-wave downward
                'downwelling_shortwave_flux_in_air_assuming_clear_sky': ['SWGDNCLR'], # [W/m2] short-wave downward assuming clear sky
                'downwelling_longwave_flux_in_air_assuming_clear_sky': ['LWGDNCLR']} # [W/m2] long-wave downward assuming clear sky
        varlist = self.TranslateCF2short(dpar)                           
        self.MERRA2station(path.join(self.dir_inp,'merra_sr_*.nc'), 
                         path.join(self.dir_out,'merra_sr_' + 
                                    self.list_name + '.nc'), self.stations,
                                    varlist, date = self.date)          
                        
        # NEED ADD 'H' in it!
        # === 2D Interpolation for Pressure-Level, Analyzed Meteorological DATA ===
        # dictionary to translate CF Standard Names into MERRA2
        # pressure level variable keys. 
        dpar = {'air_temperature'   : ['T'],           # [K]
                'wind_speed'        : ['U', 'V'],      # [m s-1]
                'relative_humidity' : ['RH']}          # [1]
        varlist = self.TranslateCF2short(dpar).append('H')
        self.MERRA2station(path.join(self.dir_inp,'merra_pl_*.nc'), 
                         path.join(self.dir_out,'merra_pl_' + 
                                    self.list_name + '.nc'), self.stations,
                                    varlist, date = self.date)  
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        
        # 1D Interpolation for Pressure Level Analyzed Meteorological Data 
        self.levels2elevation(path.join(self.dir_out,'merra_pl_' + 
                                        self.list_name + '.nc'), 
                              path.join(self.dir_out,'merra_pl_' + 
                                        self.list_name + '_surface.nc'))

      
class MERRAscale(object):
    """
    Class for MERRA data that has methods for scaling station data to
    better resemble near-surface fluxes.
    
    Processing kernels have names in UPPER CASE.
       
    Args:
        sfile: Full path to a Globsim Scaling Parameter file. 
              
    Example:          
        MERRAd = MERRAscale(sfile) 
        MERRAd.process()
    """
        
    def __init__(self, sfile):
        # read parameter file
        self.sfile = sfile
        par = ParameterIO(self.sfile)
        
        # read kernels
        self.kernels = par.kernels
        if not isinstance(self.kernels, list):
            self.kernels = [self.kernels]
            
        # input file names
        self.nc_pl = nc.Dataset(path.join(par.project_directory,'merra2/merra_pl_' + 
                                par.list_name + '_surface.nc'), 'r')
        self.nc_sa = nc.Dataset(path.join(par.project_directory,'merra2/merra_sa_' + 
                                par.list_name + '.nc'), 'r')
        self.nc_sr = nc.Dataset(path.join(par.project_directory,'merra2/merra_sr_' + 
                                par.list_name + '.nc'), 'r')
        self.nc_sc = nc.Dataset(path.join(par.project_directory,'merra2/merra_sc_' + 
                                par.list_name + '.nc'), 'r')
        self.nstation = len(self.nc_sc.variables['station'][:])                        
                              
        # output file 
        self.outfile = par.output_file  
        
        # time vector for output data
        # get time and convert to datetime object
        nctime = self.nc_pl.variables['time'][:]
        self.t_unit = self.nc_pl.variables['time'].units #"hours since 1980-01-01 00:00:0.0"
        self.t_cal  = self.nc_pl.variables['time'].calendar
        time = nc.num2date(nctime, units = self.t_unit, calendar = self.t_cal)
        
        #number of time steps
        self.nt = int(floor((max(time) - min(time)).total_seconds() 
                      / 3600 / par.time_step))+1 # +1 : include last value
        self.time_step = par.time_step * 3600 # [s] scaled file
        
        # vector of output time steps as datetime object
        # 'seconds since 1980-01-01 00:00:0.0'
        mt = min(time)
        self.times_out = [mt + timedelta(seconds = (x*self.time_step)) 
                          for x in range(0, self.nt)]                                                                   

        # vector of output time steps as written in ncdf file
        units = 'seconds since 1980-01-01 00:00:0.0'
        self.times_out_nc = nc.date2num(self.times_out, 
                                        units = units, 
                                        calendar = self.t_cal) 
        
    def process(self):
        """
        Run all relevant processes and save data. Each kernel processes one 
        variable and adds it to the netCDF file.
        """    
        self.rg = ScaledFileOpen(self.outfile, self.nc_pl, self.times_out_nc)
        
        # iterate thorugh kernels and start process
        for kernel_name in self.kernels:
            getattr(self, kernel_name)()
            
        # self.conv_geotop()    
            
        # close netCDF files   
        self.rg.close()
        self.nc_pl.close()
        self.nc_sr.close()
        self.nc_sa.close()
        self.nc_sc.close()

    def PRESS_MERRA_Pa_pl(self):
        """
        Surface air pressure from pressure levels.
        """        
        # add variable to ncdf file
        vn = 'AIRT_PRESS_Pa_pl' # variable name
        var           = self.rg.createVariable(vn,'f4',('time','station'))    
        var.long_name = 'air_pressure MERRA-2 pressure levels only'
        var.units     = 'Pa'.encode('UTF8')  
        
        # interpolate station by station
        time_in = self.nc_pl.variables['time'][:].astype(np.int64)  
        values  = self.nc_pl.variables['air_pressure'][:]                   
        for n, s in enumerate(self.rg.variables['station'][:].tolist()): 
            #scale from hPa to Pa 
            self.rg.variables[vn][:, n] = series_interpolate(self.times_out_nc, 
                                        time_in*3600, values[:, n]) * 100          

    def AIRT_MERRA_C_pl(self):
        """
        Air temperature derived from pressure levels, exclusively.
        """        
        vn = 'AIRT_MERRA2_C_pl' # variable name
        var           = self.rg.createVariable(vn,'f4',('time','station'))    
        var.long_name = 'air_temperature MERRA2 pressure levels only'
        var.units     = self.nc_pl.variables['T'].units.encode('UTF8')  
        
        # interpolate station by station
        time_in = self.nc_pl.variables['time'][:].astype(np.int64)
        values  = self.nc_pl.variables['T'][:]                   
        for n, s in enumerate(self.rg.variables['station'][:].tolist()):  
            self.rg.variables[vn][:, n] = series_interpolate(self.times_out_nc, 
                                            time_in*3600, values[:, n]-273.15)            


    def AIRT_MERRA_C_sur(self):
        """
        Air temperature derived from surface data, exclusively.
        """   
        
        # add variable to ncdf file
        vn = 'AIRT_MERRA2_C_sur' # variable name
        var           = self.rg.createVariable(vn,'f4',('time', 'station'))    
        var.long_name = '2_metre_temperature MERRA2 surface only'
        var.units     = self.nc_sa.variables['T2M'].units.encode('UTF8')  
        
        # interpolate station by station
        time_in = self.nc_sa.variables['time'][:].astype(np.int64)
        values  = self.nc_sa.variables['T2M'][:]                   
        for n, s in enumerate(self.rg.variables['station'][:].tolist()):  
            self.rg.variables[vn][:, n] = series_interpolate(self.times_out_nc, 
                                                    time_in*3600, 
                                                    values[:, n]-273.15)            

    def RH_MERRA_per_sur(self):
        """
        Relative Humdity derived from surface data, exclusively.Clipped to
        range [0.1,99.9]. Kernel AIRT_MERRA_C_sur must be run before.
        """   
        
        # temporary variable,  interpolate station by station
        dewp = np.zeros((self.nt, self.nstation), dtype=np.float32)
        time_in = self.nc_sa.variables['time'][:].astype(np.int64)
        values  = self.nc_sa.variables['T2MDEW'][:]                   
        for n, s in enumerate(self.rg.variables['station'][:].tolist()):  
            dewp[:, n] = series_interpolate(self.times_out_nc, 
                                            time_in*3600, values[:, n]-273.15) 
                                                             
        # add variable to ncdf file
        vn = 'RH_MERRA2_per_sur' # variable name
        var           = self.rg.createVariable(vn,'f4',('time', 'station'))    
        var.long_name = 'Relative humidity MERRA2 surface only'
        var.units     = 'Percent'
        
        # simple: https://en.wikipedia.org/wiki/Dew_point
        RH = 100 - 5 * (self.rg.variables['AIRT_MERRA2_C_sur'][:, :] - dewp[:, :])
        self.rg.variables[vn][:, :] = RH.clip(min=0.1, max=99.9)    
                                                    

    def WIND_MERRA_sur(self):
        """
        Wind speed and direction at 10 metre derived from surface data, exclusively.
        """   
        
        # temporary variable, interpolate station by station
        U = np.zeros((self.nt, self.nstation), dtype=np.float32)        
        time_in = self.nc_sa.variables['time'][:].astype(np.int64)
        values  = self.nc_sa.variables['U10M'][:]                   
        for n, s in enumerate(self.rg.variables['station'][:].tolist()):  
            U[:, n] = series_interpolate(self.times_out_nc, 
                                         time_in*3600, values[:, n]) 

        # temporary variable, interpolate station by station
        V = np.zeros((self.nt, self.nstation), dtype=np.float32)        
        time_in = self.nc_sa.variables['time'][:].astype(np.int64)
        values  = self.nc_sa.variables['V10M'][:]                   
        for n, s in enumerate(self.rg.variables['station'][:].tolist()):  
            V[:, n] = series_interpolate(self.times_out_nc, 
                                         time_in*3600, values[:, n])
                                          
        # add variable to ncdf file
        vn = 'WSPD_MERRA2_ms_sur' # variable name
        var           = self.rg.createVariable(vn,'f4',('time', 'station'))    
        var.long_name = '10 metre wind speed MERRA-2 surface only'
        var.units     = 'm s**-1' 
        self.rg.variables[vn][:, :] = np.sqrt(np.power(V,2) + np.power(U,2))  
 
        # add variable to ncdf file
        vn = 'WDIR_MERRA2_deg_sur' # variable name
        var           = self.rg.createVariable(vn,'f4',('time', 'station'))    
        var.long_name = '10 metre wind direction MERRA-2 surface only'
        var.units     = 'deg' 
        self.rg.variables[vn][:, :] = np.mod(np.degrees(np.arctan2(V,U))-90,360) 
                                         
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
    def SW_MERRA_Wm2_sur(self):
        """
        solar radiation downwards derived from surface data, exclusively.
        """   
        
        # add variable to ncdf file
        vn = 'SW_MERRA2_Wm2_sur' # variable name
        var           = self.rg.createVariable(vn,'f4',('time', 'station'))    
        var.long_name = 'Surface solar radiation downwards MERRA-2 surface only'
        var.units     = self.nc_sr.variables['SWGDN'].units.encode('UTF8')  

        # interpolate station by station
        time_in = self.nc_sr.variables['time'][:].astype(np.int64)  
        values  = self.nc_sr.variables['SWGDN'][:]                                
        for n, s in enumerate(self.rg.variables['station'][:].tolist()):  
            self.rg.variables[vn][:, n] = series_interpolate(self.times_out_nc, 
                                          time_in*3600, values[:, n]) 

    def LW_MERRA_Wm2_sur(self):
        """
        Long-wave radiation downwards derived from surface data, exclusively.
        """   
        
        # add variable to ncdf file
        vn = 'LW_MERRA2_Wm2_sur' # variable name
        var           = self.rg.createVariable(vn,'f4',('time', 'station'))    
        var.long_name = 'Surface thermal radiation downwards MERRA-2 surface only'
        var.units     = self.nc_sr.variables['LWGDN'].units.encode('UTF8')  

        # interpolate station by station
        time_in = self.nc_sr.variables['time'][:].astype(np.int64)
        values  = self.nc_sr.variables['LWGDN'][:]                                
        for n, s in enumerate(self.rg.variables['station'][:].tolist()):  
            self.rg.variables[vn][:, n] = series_interpolate(self.times_out_nc, 
                                          time_in*3600, values[:, n]) 

    def PREC_MERRA_mm_sur(self):
        """
        Precipitation derived from surface data, exclusively.
        Convert units: kg/m2/s to mm/time_step (hours)
        1 kg/m2 = 1mm
        """   
        
        # add variable to ncdf file
        vn = 'PREC_MERRA2_mm_sur' # variable name
        var           = self.rg.createVariable(vn,'f4',('time', 'station'))    
        var.long_name = 'Total precipitation MERRA2 surface only'
        var.units     = 'mm'.encode('UTF8')  
        
        # interpolate station by station
        time_in = self.nc_sa.variables['time'][:].astype(np.int64)
        values  = self.nc_sa.variables['PRECTOTCORR'][:]
        for n, s in enumerate(self.rg.variables['station'][:].tolist()): 
            self.rg.variables[vn][:, n] = series_interpolate(self.times_out_nc, 
                                          time_in*3600, values[:, n]) * self.time_step            


    def SH_MERRA_kgkg_sur(self):
        '''
        Specific humidity [kg/kg]
        https://crudata.uea.ac.uk/cru/pubs/thesis/2007-willett/2INTRO.pdf
        '''
        
        # temporary variable,  interpolate station by station
        dewp = np.zeros((self.nt, self.nstation), dtype=np.float32)
        time_in = self.nc_sa.variables['time'][:].astype(np.int64)  
        values  = self.nc_sa.variables['T2MDEW'][:]                   
        for n, s in enumerate(self.rg.variables['station'][:].tolist()):  
            dewp[:, n] = series_interpolate(self.times_out_nc, 
                                            time_in*3600, values[:, n]-273.15) 

        # compute
        SH = spec_hum_kgkg(dewp[:, :], 
                           self.rg.variables['AIRT_PRESS_Pa_pl'][:, :])  
        
        # add variable to ncdf file
        vn = 'SH_MERRA_kgkg_sur' # variable name
        var           = self.rg.createVariable(vn,'f4',('time', 'station'))    
        var.long_name = 'Specific humidity MERRA-2 surface only'
        var.units     = 'Kg/Kg'.encode('UTF8')  
        self.rg.variables[vn][:, :] = SH                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                

  

