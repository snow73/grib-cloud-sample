FROM ubuntu:latest

RUN apt-get update \
&&  apt-get -y install \
    wget \
    bzip2 \
    git \
    gcc \
    cmake \
    gfortran \
    libopenjpeg-dev \
    libpng-dev \
    libnetcdf-dev \
    python \
    python-tables \
    hdf5-tools \
    libhdf5-dev \
    libhdf5-serial-dev\
    python-numpy \
    python-netcdf4 \
    python-tk \
    python-pip \
    vim \
    && apt-get clean

RUN pip --no-cache-dir install --upgrade pip \
    && pip --no-cache-dir install numpy netcdf4 matplotlib pyproj

RUN mkdir geos \
    && cd geos \
    && mkdir build \
    && wget -O geos.tar.bz2 "http://download.osgeo.org/geos/geos-3.6.2.tar.bz2" \
    && bzip2 -d geos.tar.bz2 \
    && tar -xvf geos.tar \
    && rm geos.tar \
    && cd geos-3.6.2 \
    && ./configure \
    && make \
    && make check \
    && make install \
    && pwd \
    && rm -rf /geos

RUN mkdir basemap \
    && cd basemap \
    && mkdir build \
    && wget -O basemap.tar.gz "https://codeload.github.com/matplotlib/basemap/tar.gz/v1.1.0" \
    && tar -xzf basemap.tar.gz \
    && rm basemap.tar.gz \
    && cd basemap-1.1.0 \
    && python setup.py install \
    && cd examples \
#    && python simpletest.py \
    && pwd \
    && rm -rf /basemap
    
RUN mkdir eccodes \
    && cd eccodes \
    && mkdir build \
    && cd build \
    && wget -O eccodes_test_data.tar.gz  "http://download.ecmwf.org/test-data/grib_api/eccodes_test_data.tar.gz" \
    && tar -xzf eccodes_test_data.tar.gz \
    && rm eccodes_test_data.tar.gz \
    && cd /eccodes \
    && wget -O eccodes.tar.gz "https://software.ecmwf.int/wiki/download/attachments/45757960/eccodes-2.4.1-Source.tar.gz?api=v2" \
    && tar -xzf eccodes.tar.gz \
    && cd build \
    && pwd \
    && cmake -DCMAKE_INSTALL_PREFIX=/usr/local -DENABLE_PYTHON=ON -DENABLE_MEMFS=ON -DENABLE_PNG=ON ../eccodes-2.4.1-Source \
    && make \
    && ctest \
    && make install \
    && pwd \
    && rm -rf /eccodes

WORKDIR /app

COPY app /app

COPY cmd.sh /

CMD ["/cmd.sh"]
