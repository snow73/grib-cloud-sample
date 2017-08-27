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
from subprocess import call
from dateutil.parser import parse
from mpl_toolkits.basemap import Basemap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

tmpgrb = '/tmp/grib.grb2'
clevs = np.arange(-25,45.,5.)
missingValue = 1e+20 # A value out of range

m = Basemap(width=5400000,height=4200000,
            resolution='l',projection='eqdc',\
            lat_1=48.,lat_2=62,lat_0=54,lon_0=10.)

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

            ni = 0
            nj = 0

            for j in range(mcount):
                gid = gid_list[j]
 
                if ni == 0:
                    ni = codes_get (gid, "Ni")
                    nj = codes_get (gid, "Nj")

                    latitudeOfFirstGridPointInDegrees  = codes_get (gid, "latitudeOfFirstGridPointInDegrees")
                    longitudeOfFirstGridPointInDegrees = codes_get (gid, "longitudeOfFirstGridPointInDegrees")
                    latitudeOfLastGridPointInDegrees  = codes_get (gid, "latitudeOfLastGridPointInDegrees")
                    longitudeOfLastGridPointInDegrees = codes_get (gid, "longitudeOfLastGridPointInDegrees")

                    lons = np.linspace (longitudeOfFirstGridPointInDegrees-360., longitudeOfLastGridPointInDegrees, ni, endpoint = True)
                    lats = np.linspace (latitudeOfFirstGridPointInDegrees, latitudeOfLastGridPointInDegrees, nj, endpoint = True)
                    xx, yy = m(*np.meshgrid(lons,lats))

                print "processing message number",j+1

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

                values = codes_get_values(gid).reshape(nj,ni)
                values = values - 273.15

                codes_release(gid)

                fig = plt.figure()
                cs = m.contourf(xx,yy,values,clevs,cmap=plt.cm.jet)

                # if j == 0:
                plt.colorbar(cs, orientation="horizontal", shrink=0.7, pad=0.05)

                m.drawcoastlines()
                m.drawcountries()
                m.drawparallels(np.arange(-90,90,30))
                m.drawmeridians(np.arange(0,360,30))

                plt.title("{0:s}\n{1} ({2} {3})".format(parametername, validitytime, modeltime, steps))
                plt.savefig('plot.png')
                plt.close(fig)

                client = boto3.client('s3', 'eu-west-1')
                transfer = boto3.s3.transfer.S3Transfer(client)
                transfer.upload_file("plot.png", "nwp.fmi.hirlam-public", "basemap/" + targetname, extra_args={'ContentType': "image/png"})

            call(["cp", "index.tmpl", "index.html"])
            call(["sed", "-i", "-e" "s/MODELRUNTIME/{}/g".format(modeltime.strftime("%Y%m%d%H%M")), "index.html"])
            transfer.upload_file("index.html", "nwp.fmi.hirlam-public", "index.html", extra_args={'ContentType': "text/html"})

        message.delete()
    time.sleep(1)
