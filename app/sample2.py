from mpl_toolkits.basemap import Basemap
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

map = Basemap(projection='ortho', lat_0=50, lon_0=-100, resolution='l', area_thresh=1000.0)

map.drawcoastlines() 
map.drawcountries() 
map.fillcontinents(color='coral') 
map.drawmapboundary()

map.drawmeridians(np.arange(0, 360, 30)) 
map.drawparallels(np.arange(-90, 90, 30))

plt.savefig('graph2.png')
