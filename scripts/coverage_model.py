"""Terrain line-of-sight radar coverage, following the method ATC-425 describes.

A 4/3-Earth-radius model accounts for standard refraction. A target at a given height above the
ground under it is visible when its elevation angle from the antenna clears every terrain sample
nearer the radar on the same radial. Beam patterns, clutter and sensitivity are not modeled.
"""
import math
import numpy as np
EARTH_RADIUS_M=6371008.8
EFFECTIVE_RADIUS_M=EARTH_RADIUS_M*4/3
FT=0.3048
def destination(lat,lon,azimuth_deg,distance_m):
    """Great-circle destination points; azimuth and distance broadcast."""
    p1,l1=math.radians(lat),math.radians(lon);a=np.radians(azimuth_deg);d=np.asarray(distance_m)/EARTH_RADIUS_M
    p2=np.arcsin(np.sin(p1)*np.cos(d)+np.cos(p1)*np.sin(d)*np.cos(a))
    l2=l1+np.arctan2(np.sin(a)*np.sin(d)*np.cos(p1),np.cos(d)-np.sin(p1)*np.sin(p2))
    return np.degrees(p2),(np.degrees(l2)+540)%360-180
def bearing_distance(lat,lon,lats,lons):
    """Initial bearing (degrees) and great-circle distance (m) from one point to many."""
    p1,l1=math.radians(lat),math.radians(lon);p2,l2=np.radians(lats),np.radians(lons)
    y=np.sin(l2-l1)*np.cos(p2);x=math.cos(p1)*np.sin(p2)-math.sin(p1)*np.cos(p2)*np.cos(l2-l1)
    h=np.sin((p2-p1)/2)**2+math.cos(p1)*np.cos(p2)*np.sin((l2-l1)/2)**2
    return (np.degrees(np.arctan2(y,x))+360)%360,2*EARTH_RADIUS_M*np.arcsin(np.sqrt(np.clip(h,0,1)))
def elevation_angle(range_m,height_m,antenna_m):
    """Apparent elevation angle (radians, small-angle) of a point under the 4/3-Earth model."""
    return (height_m-antenna_m)/range_m-range_m/(2*EFFECTIVE_RADIUS_M)
def visibility(ranges_m,terrain_m,antenna_m,heights_agl_m):
    """Boolean [slice, azimuth, range] grid: target at each height AGL is in line of sight.

    terrain_m is [azimuth, range] ground elevation sampled along each radial at ranges_m.
    """
    terrain_angle=elevation_angle(ranges_m,terrain_m,antenna_m)
    # Highest terrain angle strictly nearer the radar on each radial.
    blocking=np.maximum.accumulate(terrain_angle,axis=1)
    blocking=np.concatenate([np.full((terrain_m.shape[0],1),-np.inf),blocking[:,:-1]],axis=1)
    return np.stack([elevation_angle(ranges_m,terrain_m+h,antenna_m)>=blocking for h in heights_agl_m])
def horizon_range_m(antenna_agl_m,target_agl_m):
    """Smooth-Earth radar horizon for sea-level terrain (used to check the model)."""
    return math.sqrt(2*EFFECTIVE_RADIUS_M*antenna_agl_m)+math.sqrt(2*EFFECTIVE_RADIUS_M*target_agl_m)
