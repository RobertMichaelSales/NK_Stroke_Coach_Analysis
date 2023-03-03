import os
import io
import time
import matplotlib
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import urllib.request

from PIL import Image
from matplotlib.collections import LineCollection
from mpl_toolkits.axes_grid1 import make_axes_locatable

#==============================================================================
def LoadRowingData(fname):

    names = np.genfromtxt(fname=fname,dtype=str,delimiter=",",skip_header=28,usecols=(1,3,4,5,8,9,10,22,23))[0]
    units = np.genfromtxt(fname=fname,dtype=str,delimiter=",",skip_header=29,usecols=(1,3,4,5,8,9,10,22,23))[0]
    value = np.genfromtxt(fname=fname,dtype=str,delimiter=",",skip_header=30,usecols=(1,3,4,5,8,9,10,22,23))
    
    data = {}
    
    for index,name in enumerate(names):
        
        data[name] = InterpretString(value[:,index])
    
    return data

#==============================================================================

def ReadSessionDateTime(fname):
    
    import datetime
    
    date_string = fname.split(" ")[-2]
    date_y = int(date_string[0:4])
    date_m = int(date_string[4:6])
    date_d = int(date_string[6:8])
    
    time_string = fname.split(" ")[-1]
    time_h = int(time_string[0:2])
    time_m = int(time_string[2:4])
    
    session = datetime.datetime(date_y,date_m,date_d,time_h,time_m)
        
    session_datetime = session.strftime("%a %d %b %Y - %H:%M %p")
    
    return session_datetime

#==============================================================================
    
def InterpretString(list_of_strings):
    
    data = np.zeros(shape=list_of_strings.shape)
    
    for index,string in enumerate(list_of_strings):
    
        try:
            
            value = float(string)
            
        except:
            
            value = np.sum(np.array([float(x) for x in string.split(":")]) * [3600.0,60.0,1.0])
        
        data[index] = value
        
    return data

#==============================================================================
# Geo-coordinate (lon) -> Pixel coordinate (x)
def LonToPix(lon,zoom):
    
    zoom_size_0 = 512
    
    lon = np.radians(lon)
    
    x = (zoom_size_0 / (2 * np.pi)) * (2**zoom) * (lon + np.pi)
    
    return x

#==============================================================================
# Geo-coordinate (lat) -> Pixel coordinate (y)
def LatToPix(lat,zoom):
    
    zoom_size_0 = 512
    
    lat = np.radians(lat)
        
    y = (zoom_size_0 / (2 * np.pi)) * (2**zoom) * (np.pi - np.log(np.tan((np.pi/4)+(lat/2))))
    
    return y

#==============================================================================
# Pixel coordinate (x) -> Geo-coordinate (lon)
def PixToLon(x,zoom):
        
    zoom_size_0 = 512
    
    lon = (((2 * np.pi) / zoom_size_0) * (x / (2**zoom))) - np.pi
    
    lon = np.degrees(lon)

    return lon

#==============================================================================
# Pixel coordinate (y) -> Geo-coordinate (lat)
def PixToLat(y,zoom):
    
    zoom_size_0 = 512
    
    lat = (2 * np.arctan(np.exp(np.pi - (((2 * np.pi) / zoom_size_0) * (y / (2**zoom)))))) - (np.pi / 2)
    
    lat = np.degrees(lat)
    
    return lat

#==============================================================================
# Obtain the map for the provided bounding box
def GetMapFromBoundingBox(bbox):
    
    # The API token from https://www.mapbox.com/api-documentation/maps/#static
    token = "pk.eyJ1IjoiYnVzeWJ1cyIsImEiOiJjanF4cXNoNmEwOG1yNDNycGw5bTByc3g5In0.flzpO633oGAY5aa-RQa4Ow"

    # The region of interest in latitude and longitude geo-coordinates
    bbox_lon_min,bbox_lon_max,bbox_lat_min,bbox_lat_max = bbox

    # Rendered image map size in pixels as it should come from MapBox
    w,h = 1024,1024

    # The mid-point of the region of interest
    lon = round(np.average([bbox_lon_min,bbox_lon_max]),5)
    lat = round(np.average([bbox_lat_min,bbox_lat_max]),5)

    # Look for appropriate zoom level to cover the region of interest
    for zoom in range(16,0,-1):
        
        # Center point in pixel coordinates at the current zoom level
        x = LonToPix(lon=lon,zoom=zoom)
        y = LatToPix(lat=lat,zoom=zoom)

        x_min = x - (w/2)
        x_max = x + (w/2)
        y_min = y - (h/2)
        y_max = y + (h/2)

        mbox_lon_min = PixToLon(x=x_min,zoom=zoom)
        mbox_lon_max = PixToLon(x=x_max,zoom=zoom)
        mbox_lat_max = PixToLat(y=y_min,zoom=zoom)
        mbox_lat_min = PixToLat(y=y_max,zoom=zoom)
            
        if (mbox_lon_min <= bbox_lon_min) and (bbox_lon_max <= mbox_lon_max):
            if (mbox_lat_min <= bbox_lat_min) and (bbox_lat_max <= mbox_lat_max):   
                break
            else: pass
        else: pass
    ##          
        
    # Collect all parameters
    params = {
        'style'     : "streets-v12",
        'lat'       : lat,
        'lon'       : lon,
        'token'     : token,
        'zoom'      : zoom,
        'w'         : w,
        'h'         : h,
        'retina'    : "@2x"
        }

    url_template = "https://api.mapbox.com/styles/v1/mapbox/{style}/static/{lon},{lat},{zoom}/{w}x{h}{retina}?access_token={token}&attribution=false&logo=false"
    url = url_template.format(**params)

    # Download the rendered image
    with urllib.request.urlopen(url) as response:
        whole_map = Image.open(io.BytesIO(response.read()))

    # If the retina @2x parameter is used the image is twice the requested size
    w,h = whole_map.size

    # Extract the region of interest from the larger covering map
    cropped_map = whole_map.crop((
        round(w * (bbox_lon_min - mbox_lon_min) / (mbox_lon_max - mbox_lon_min)),
        round(h * (bbox_lat_max - mbox_lat_max) / (mbox_lat_min - mbox_lat_max)),
        round(w * (bbox_lon_max - mbox_lon_min) / (mbox_lon_max - mbox_lon_min)),
        round(h * (bbox_lat_min - mbox_lat_max) / (mbox_lat_min - mbox_lat_max)),
    ))

    return cropped_map
    
#==============================================================================

def GetBBox(fname,stroke_slice=None,space=0):
    
    data = LoadRowingData(fname)
    
    if stroke_slice:
        indices = slice(stroke_slice[0],stroke_slice[1]-1)
    else:
        indices = slice(0,(data["Total Strokes"].size -1))
        
    lat = data["GPS Lat."]
    lon = data["GPS Lon."]
    
    lat_slice = lat[indices]
    lon_slice = lon[indices]
    
    lat_min,lat_max = lat_slice.min(),lat_slice.max()
    lon_min,lon_max = lon_slice.min(),lon_slice.max()
    
    lat_avg = (lat_min+lat_max)/2
    lon_avg = (lon_min+lon_max)/2
    
    print("Lat. Min: {:9.6f}, Max: {:9.6f}, Avg: {:9.6f}".format(lat_min,lat_max,lat_avg))
    print("Lon. Min: {:9.6f}, Max: {:9.6f}, Avg: {:9.6f}".format(lon_min,lon_max,lon_avg))
    
    bbox = (lon_min-space,lon_max+space,lat_min-space,lat_max+space) 

    return bbox

#==============================================================================

def PlotGPS(fname,stroke_slice=None,save=True):

    plt.style.use("/home/rms221/Documents/Compressive_Neural_Representations_Tensorflow/NeurComp_SourceCode/Auxiliary_Scripts/plot.mplstyle")  
    params_plot = {'text.latex.preamble': [r'\usepackage{amsmath}',r'\usepackage{amssymb}'],'axes.grid': True}
    matplotlib.rcParams.update(params_plot) 
    
    space = 0.001
    
    data = LoadRowingData(fname)
    bbox = GetBBox(fname=fname,stroke_slice=stroke_slice,space=space)
    my_map = GetMapFromBoundingBox(bbox=bbox)
    
    fig, ax = plt.subplots(nrows=1,ncols=1,figsize=(8,5),constrained_layout=False)
    
    if stroke_slice:
        indices = slice(stroke_slice[0],stroke_slice[1]-1)
    else:
        indices = slice(0,(data["Total Strokes"].size -1))
    
    lat = data["GPS Lat."]
    lon = data["GPS Lon."]
    vel = data["Speed (GPS)"]
    
    lat_slice = lat[indices]
    lon_slice = lon[indices]
    vel_slice = vel[indices]
    
    norm = plt.Normalize(vel_slice.min(),vel_slice.max())
    
    gps_data = np.array([lon_slice,lat_slice]).T.reshape(-1, 1, 2)
    segments = np.concatenate([gps_data[:-1],gps_data[1:]],axis=1)
    line_collection = LineCollection(segments,cmap='plasma',norm=norm,path_effects=[path_effects.Stroke(capstyle="round")],linewidth=3)
        
    line_collection.set_array(vel_slice)
    line_collection.set_linewidth(2)
    line = ax.add_collection(line_collection)

    the_divider = make_axes_locatable(ax)
    color_axis = the_divider.append_axes("right", size="5%", pad=0.1)
    cbar = plt.colorbar(line, cax=color_axis)
    cbar.set_label('Boat Speed [$m/s$]')
    
    ax.imshow(my_map,extent=(bbox))
    
    ax.set_xlim(lon_slice.min()-space,lon_slice.max()+space)
    ax.set_ylim(lat_slice.min()-space,lat_slice.max()+space)
    ax.set_xlabel(r"Longitude  [deg.]")
    ax.set_ylabel(r"Latitude  [deg.]")
    
    ax.set_aspect('equal')
    
    session_datetime = ReadSessionDateTime(fname)
    session_savename = session_datetime.replace(":","").replace(" - "," ").replace(" ","_").lower() + "_gps.png"
    
    if save:
        savename = os.path.join(os.getcwd(),"session_graphs",session_savename)
        plt.savefig(savename)
    else: pass

    plt.show()

#==============================================================================

def PlotGraphsVsNStrokes(fname,stroke_slice=None,save=True):
    
    plt.style.use("plot.mplstyle")      
    params_plot = {'text.latex.preamble': [r'\usepackage{amsmath}',r'\usepackage{amssymb}'],'axes.grid': True}
    matplotlib.rcParams.update(params_plot) 
    
    data = LoadRowingData(fname)
    
    if stroke_slice:
        indices = slice(stroke_slice[0],stroke_slice[1]-1)
    else:
        indices = slice(0,(data["Total Strokes"].size -1))
    
    split = data["Split (GPS)"][indices]
    stroke_rate = data["Stroke Rate"][indices]
    total_strokes = data["Total Strokes"][indices]
    distance_per_stroke = data["Distance/Stroke (GPS)"][indices]
    
    fig, ax = plt.subplots(nrows=3,ncols=1,figsize=(30,10),constrained_layout=False,sharex=True)
 
    ax[0].plot(total_strokes,split              ,color="b",marker="s",fillstyle="full",markerfacecolor="w")
    ax[1].plot(total_strokes,stroke_rate        ,color="r",marker="o",fillstyle="full",markerfacecolor="w")
    ax[2].plot(total_strokes,distance_per_stroke,color="g",marker="o",fillstyle="full",markerfacecolor="w")
    
    ax[0].set_xlim(total_strokes[0],total_strokes[-1])
    ax[0].set_ylim(90,160)
    
    ax[-1].set_xlabel(r"Stroke Count [ - ]")
    
    ax[0].set_ylabel(r"Split (GPS) [ minutes : seconds ]",color="b",labelpad=10)
    ax[1].set_ylabel(r"Stroke Rate [ strokes / minute ]" ,color="r",labelpad=10)
    ax[2].set_ylabel(r"Disance Per Stroke [ metres / - ]",color="g",labelpad=10)
    
    formatter = matplotlib.ticker.FuncFormatter(lambda s, x: time.strftime('%M:%S', time.gmtime(s)))
    ax[0].yaxis.set_major_formatter(formatter)
    
    fig.align_ylabels()
    
    session_datetime = ReadSessionDateTime(fname)
    session_savename = session_datetime.replace(":","").replace(" - "," ").replace(" ","_").lower() + "_analysis1.png"
    
    if save:
        savename = os.path.join(os.getcwd(),"session_graphs",session_savename)
        plt.savefig(savename)
    else: pass

    plt.show()
    
    return None

#==============================================================================

def PlotGraphsVsDistance(fname,stroke_slice=None,save=True):
    
    plt.style.use("plot.mplstyle")  
    params_plot = {'text.latex.preamble': [r'\usepackage{amsmath}',r'\usepackage{amssymb}'],'axes.grid': True}
    matplotlib.rcParams.update(params_plot) 
    
    data = LoadRowingData(fname)
    
    if stroke_slice:
        indices = slice(stroke_slice[0],stroke_slice[1]-1)
    else:
        indices = slice(0,(data["Total Strokes"].size -1))
    
    split = data["Split (GPS)"][indices]
    distance = data["Distance (GPS)"][indices]
    stroke_rate = data["Stroke Rate"][indices]
    distance_per_stroke = data["Distance/Stroke (GPS)"][indices]
    
    fig, ax = plt.subplots(nrows=3,ncols=1,figsize=(30,10),constrained_layout=False,sharex=True)
 
    ax[0].plot(distance,split              ,color="b",marker="s",fillstyle="full",markerfacecolor="w")
    ax[1].plot(distance,stroke_rate        ,color="r",marker="o",fillstyle="full",markerfacecolor="w")
    ax[2].plot(distance,distance_per_stroke,color="g",marker="o",fillstyle="full",markerfacecolor="w")
    
    ax[0].set_xlim(distance[0],distance[-1])
    ax[0].set_ylim(90,160)
    
    ax[-1].set_xlabel(r"Distance [ metres ]")
    
    ax[0].set_ylabel(r"Split (GPS) [ minutes : seconds ]",color="b",labelpad=10)
    ax[1].set_ylabel(r"Stroke Rate [ strokes / minute ]" ,color="r",labelpad=10)
    ax[2].set_ylabel(r"Disance Per Stroke [ metres / - ]",color="g",labelpad=10)
    
    formatter = matplotlib.ticker.FuncFormatter(lambda s, x: time.strftime('%M:%S', time.gmtime(s)))
    ax[0].yaxis.set_major_formatter(formatter)
    
    fig.align_ylabels()
    
    session_datetime = ReadSessionDateTime(fname)
    session_savename = session_datetime.replace(":","").replace(" - "," ").replace(" ","_").lower() + "_analysis2.png"
    
    if save:
        savename = os.path.join(os.getcwd(),"session_graphs",session_savename)
        plt.savefig(savename)
    else: pass

    plt.show()

#==============================================================================

fname ="session_data/Toms Speedcoach 20230301 0617am.csv"



# stroke_slice = (640,740)
# stroke_slice = None

stroke_slice = (100,300)

PlotGPS(fname=fname,stroke_slice=stroke_slice,save=True)
# PlotGraphsVsNStrokes(fname=fname,stroke_slice=stroke_slice,save=True)
# PlotGraphsVsDistance(fname=fname,stroke_slice=stroke_slice,save=True)

#==============================================================================



