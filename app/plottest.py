#!/usr/bin/env python

import boto3
from eccodes import *
import traceback
import sys
import gribapi
import numpy as np
import os.path
import pandas as pd
import json
import time
from scipy.interpolate import griddata
from dateutil.parser import parse

tmpgrb = '/tmp/grib.grb2'
missingValue = 1e+20 # A value out of range

# Get the service resource
s3 = boto3.resource('s3')
sqs = boto3.resource('sqs', region_name='eu-west-1')

# Get the queue
queue = sqs.get_queue_by_name(QueueName='NWP_FMI_HIRLAM_Test')

# Process messages by printing out body
while True:
    for message in queue.receive_messages(10):
        data = json.loads(message.body)
        data = json.loads(data['Message']);
        objkey = data["Records"][0]["s3"]["object"]["key"]
        print(objkey)

        if "Temperature" in objkey:

            bucket = s3.Bucket('fmi-opendata-rcrhirlam-surface-grib')

            bucket.download_file (objkey, tmpgrb)


            f = open(tmpgrb)
 
            mcount = codes_count_in_file(f)
            gid_list = [codes_grib_new_from_file(f) for i in range(mcount)]
 
            f.close()

            for j in range(mcount):
                gid = gid_list[j]
 
                print "processing message number",j+1
                sys.stdout.flush()

                gribdate = codes_get (gid, "dataDate")
                gribtime = codes_get (gid, "dataTime")

                modeltime = parse ("{0:08d} {1:04d}".format(gribdate, gribtime))

                gribdate = codes_get (gid, "validityDate")
                gribtime = codes_get (gid, "validityTime")

                validitytime = parse ("{0:08d} {1:04d}".format(gribdate, gribtime))

                stepUnits = codes_get (gid, "stepUnits",ktype=str)
                startStep = codes_get (gid, "startStep",ktype=int)
                endStep   = codes_get (gid, "endStep",ktype=int)

                if startStep == endStep:
                    steps = "{0:+03d} {1:s}".format(startStep, stepUnits)
                else:
                    steps = "{0:+d}-{1:+d} {2:s}".format(startStep, endStep,stepUnits)

                parametername = codes_get (gid, "name",ktype=str)
                shortname = codes_get (gid, "shortName",ktype=str)
                targetname = "{0:s}_{1:s}_{2:03d}.png".format(shortname, modeltime.strftime("%Y%m%d%H%M"), startStep)

# Set the value representing the missing value in the field.
# Choose a missingValue that does not correspond to any real value in the data array

                codes_set(gid, "missingValue", missingValue)

                ni = codes_get (gid, "Ni")
                nj = codes_get (gid, "Nj")

                latitudeOfFirstGridPointInDegrees  = codes_get (gid, "latitudeOfFirstGridPointInDegrees")
                longitudeOfFirstGridPointInDegrees = codes_get (gid, "longitudeOfFirstGridPointInDegrees")
                latitudeOfLastGridPointInDegrees  = codes_get (gid, "latitudeOfLastGridPointInDegrees")
                longitudeOfLastGridPointInDegrees = codes_get (gid, "longitudeOfLastGridPointInDegrees")

                values = codes_get_values(gid).reshape(nj,ni)
                values = values - 273.15

                codes_release(gid)

                lons = np.linspace (longitudeOfFirstGridPointInDegrees-360., longitudeOfLastGridPointInDegrees, ni, endpoint = True)
                lats = np.linspace (latitudeOfFirstGridPointInDegrees, latitudeOfLastGridPointInDegrees, nj, endpoint = True)

                from mpl_toolkits.basemap import Basemap, shiftgrid
                import matplotlib
                matplotlib.use('Agg')
                import matplotlib.pyplot as plt

                m = Basemap(width=3600000,height=2100000,
                            resolution='l',projection='eqdc',\
                            lat_1=45.,lat_2=55,lat_0=50,lon_0=10.)

                xx, yy = m(*np.meshgrid(lons,lats))

                clevs = np.arange(-30,50.,2.)
                m.contourf(xx,yy,values,clevs,cmap=plt.cm.jet)

                m.drawcoastlines()
                m.drawcountries()
                m.drawparallels(np.arange(-90,90,30))
                m.drawmeridians(np.arange(0,360,30))

                plt.title("{0:s}\n{1} ({2} {3})".format(parametername, validitytime, modeltime, steps))
                plt.savefig('plot.png')

                client = boto3.client('s3', 'eu-west-1')
                transfer = boto3.s3.transfer.S3Transfer(client)
                transfer.upload_file("plot.png", "nwp.fmi.hirlam-public", "basemap/" + targetname)

        message.delete()
    sys.stdout.flush()
    time.sleep(5)
