"""
Use k-means to cluster climate stations.

Climate data from Global Historical Climatology Network. Using monthly
maximum and minimum temperature data.
Source: ftp://ftp.ncdc.noaa.gov/pub/data/ghcn/v3

Run script with -v flag to print distortion at each iteration.

Outputs json file with latitude, longitude and cluster assignment for
each climate station.
"""

import math
import random
import sys


def get_stationid_dict(filename):
    """ Returns a dictionary with station ids as keys and
    tuple of latitude and longitude as values. """

    USA_COUNTRY_CODE = "425"
    MAX_LAT = 49.0
    MIN_LON = -130.0

    with open(filename, "r") as f:
        rows = (parse_id_lat_lon(row) for row in f)
        # Filter ids to only continental USA.
        rows = (r for r in rows if r["station_id"][:3] == USA_COUNTRY_CODE)
        rows = (r for r in rows if r["lat"] < MAX_LAT and r["lon"] > MIN_LON)
        return dict((r["station_id"], (r["lat"], r["lon"])) for r in rows)


def parse_id_lat_lon(row):
    """ Returns dictionary of station_id, lat, lon from metadata row. """
    return {"station_id": row[:11],
            "lat": float(row[12:20]),
            "lon": float(row[21:30])}


def data_gen(filename, station_ids):
    """ Returns a generator which yields tuples of station_id and
    a list of the average monthly values. """

    MIN_YEAR = 1981
    MAX_YEAR = 2010
    MIN_NUM_VALUES = 20

    with open(filename, "r") as f:
        curr_station = ""
        curr_values = []
        for row in f:
            station_id = row[:11]
            yr = int(row[11:15])
            if station_id != curr_station:
                if curr_station != "" and len(curr_values) > MIN_NUM_VALUES:
                    yield curr_station, avg_monthly_values(curr_values)
                curr_station = station_id
                curr_values = []
            if station_id in station_ids and MIN_YEAR <= yr and yr <= MAX_YEAR:
                curr_values.append(parse_monthly_values(row))


def parse_monthly_values(row):
    """ Returns list of monthly values from data row. """
    return [int(row[n:n+5]) for n in xrange(19,115,8)]


def avg_monthly_values(ls):
    """ Returns tuple of average monthly values. """
    vals = [[x for x in l if x != -9999] for l in zip(*ls)]
    return [int(round(float(sum(l))/len(l))) for l in vals]


def initial_centroid():
    """ Returns an initial centroid for use with clustering. """

    # Base taken from the San Francisco station.
    base = [1522, 1582, 1752, 1972, 2082, 2252, 2082, 2302, 2472, 2022, 1582, 1522,
            610,  670,  720,  830,  890, 1060, 1220, 1330, 1280, 1170, 1000,  610]
    shift = random.randint(-800, 800)
    return [x + shift for x in base]


def find_closest_centroids(monthly_data, centroids):
    """ Returns a list of the index of the closest centroid
    to each row in monthly_data. """

    indices = ([dist(row[1:],c) for c in centroids] for row in monthly_data)
    indices = (min(enumerate(row), key=lambda p: p[1]) for row in indices)
    indices = (i for i,_ in indices)
    return list(indices)


def dist(u, v):
    """ Consider the input lists u and v as vectors.
    Return the length of the difference between the two vectors. """
    return math.sqrt(sum((x - y)**2 for x,y in zip(u,v)))


def compute_centroids(monthly_data, indices, k):
    """ Returns a list of new centroids by computing the mean of the data
    points assigned to each centroid. """
    n = len(monthly_data[0])
    def fn(agg, t):
        i, ls = t
        centroid = indices[i]
        agg[centroid][0] += 1
        for j in range(1,n):
            agg[centroid][j] += ls[j]
        return agg
    sums = [[0]*(n) for x in range(k)]
    sums = reduce(fn, enumerate(monthly_data), sums)
    sums = (row for row in sums if row[0])
    return [[int(round(float(x)/row[0])) for x in row[1:]] for row in sums]


def compute_distortion(monthly_data, centroids, indices):
    """ Returns distortion for data, centroids, and centroid assignments.
    This value should decrease at each iteration until the algorithm
    converges. """
    j = sum(dist(row[1:], centroids[indices[i]])**2 for i,row in enumerate(monthly_data))
    return float(j)/len(monthly_data)


def main(argv):
    verbose = len(argv) > 1 and argv[1] == "-v"

    max_metadata_filename = "data/ghcnm.tmax.v3.2.2.20140104.qca.inv"
    min_metadata_filename = "data/ghcnm.tmin.v3.2.2.20140104.qca.inv"
    stationid_latlons = get_stationid_dict(max_metadata_filename)

    # Verify that station_id in metadata for both max and min values
    min_stationid_latlons = get_stationid_dict(min_metadata_filename)
    for station_id in stationid_latlons.keys():
        if station_id not in min_stationid_latlons:
            del stationid_latlons[station_id]

    max_data_filename = "data/ghcnm.tmax.v3.2.2.20140104.qca.dat"
    min_data_filename = "data/ghcnm.tmin.v3.2.2.20140104.qca.dat"
    max_data = dict(data_gen(max_data_filename, stationid_latlons))
    min_data = dict(data_gen(min_data_filename, stationid_latlons))

    # Combine average monthly max and min values
    monthly_data = ((sid,v) for sid,v in max_data.iteritems() if sid in min_data)
    monthly_data = [[sid] + v + min_data[sid] for sid,v in monthly_data]

    # Run k-means clustering
    # Select an initial set of centroids
    k = 13
    random.seed()
    centroids = [initial_centroid() for y in range(k)]

    for i in range(100):
        indices = find_closest_centroids(monthly_data, centroids)
        centroids = compute_centroids(monthly_data, indices, k)
        if verbose:
            print "Distortion: ", compute_distortion(monthly_data, centroids, indices)

    # Output json file with centroid assignments and lat lon for each station
    print '{"type":"FeatureCollection","features":['
    for i,r in enumerate(monthly_data):
        print ('{{"type":"Feature","id":"{i}","geometry":{{"type":"Point",'
               '"coordinates":[{lon},{lat}]}},"properties":{{"idx":{idx}}}}}{comma}'
              ).format(i=i+1, idx=indices[i],
                       lat=stationid_latlons[r[0]][0],
                       lon=stationid_latlons[r[0]][1],
                       comma=("," if i < len(monthly_data)-1 else ""))
    print ']}'


if __name__ == "__main__":
    main(sys.argv)
