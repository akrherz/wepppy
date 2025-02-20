# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

from os.path import join as _join
from os.path import exists as _exists

from collections import OrderedDict

from glob import glob

import numpy as np

from wepppy.all_your_base.hydro import determine_wateryear
from .row_data import RowData, parse_units
from .report_base import ReportBase


class HillslopeWatbal(ReportBase):
    def __init__(self, wd):
        self.wd = wd

        from wepppy.nodb import Watershed
        watershed = Watershed.getInstance(wd)
        translator = watershed.translator_factory()
        output_dir = _join(wd, 'wepp/output')

        # find all the water output files
        wat_fns = glob(_join(output_dir, 'H*.wat.dat'))
        n = len(wat_fns)
        assert n > 0

        # make sure we have all of them
        for wepp_id in range(1, n+1):
            assert _exists(_join(output_dir, 'H{}.wat.dat'.format(wepp_id)))

        # create dictionaries for the waterbalance
        d = {}
        areas = {}
        years = set()

        # loop over the hillslopes
        for wepp_id in range(1, n + 1):
            # find the topaz_id
            topaz_id = translator.top(wepp=wepp_id)

            # initialize the water
            d[topaz_id] = {'Precipitation (mm)': {},
                           'Surface Runoff (mm)': {},
                           'Lateral Flow (mm)': {},
                           'Transpiration + Evaporation (mm)': {},
                           'Percolation (mm)': {},
                           # 'Total Soil Water Storage (mm)': {}
                           }

            wat_fn = _join(output_dir, 'H{}.wat.dat'.format(wepp_id))

            with open(wat_fn) as wat_fp:
                wat_data = wat_fp.readlines()[23:]

            for i, wl in enumerate(wat_data):
                OFE, J, Y, P, RM, Q, Ep, Es, Er, Dp, UpStrmQ, \
                SubRIn, latqcc, TSW, frozwt, SnowWater, QOFE, Tile, Irr, Area = wl.split()

                water_year = determine_wateryear(Y, J)

                J, Y, P, Q, Ep, Es, Er, Dp, latqcc, TSW, Area = \
                    int(J), int(Y), float(P), float(Q), float(Ep), float(Es), float(Er), float(Dp), float(latqcc), \
                    float(TSW), float(Area)

                if i == 0:
                    areas[topaz_id] = Area

                if wepp_id == 1:
                    years.add(water_year)

                if water_year not in d[topaz_id]['Precipitation (mm)']:
                    d[topaz_id]['Precipitation (mm)'][water_year] = P
                    d[topaz_id]['Surface Runoff (mm)'][water_year] = Q
                    d[topaz_id]['Lateral Flow (mm)'][water_year] = latqcc
                    d[topaz_id]['Transpiration + Evaporation (mm)'][water_year] = Ep + Es + Er
                    d[topaz_id]['Percolation (mm)'][water_year] = Dp
                    # d[topaz_id]['Total Soil Water Storage (mm)'][water_year] = TSW
                else:
                    d[topaz_id]['Precipitation (mm)'][water_year] += P
                    d[topaz_id]['Surface Runoff (mm)'][water_year] += Q
                    d[topaz_id]['Lateral Flow (mm)'][water_year] += latqcc
                    d[topaz_id]['Transpiration + Evaporation (mm)'][water_year] += Ep + Es + Er
                    d[topaz_id]['Percolation (mm)'][water_year] += Dp
                    # d[topaz_id]['Total Soil Water Storage (mm)'][water_year] += TSW

        self.years = sorted(years)
        self.data = d
        self.areas = areas
        self.wsarea = float(np.sum(list(areas.values())))
        self.last_top = topaz_id

    @property
    def header(self):
        return list(self.data[self.last_top].keys())

    @property
    def yearly_header(self):
        return ['Year'] + list(self.hdr)

    @property
    def yearly_units(self):
        return [None] + list(self.units)

    def yearly_iter(self):
        data = self.data
        areas = self.areas
        wsarea = self.wsarea
        header = self.header
        years = self.years

        for y in years:
            row = OrderedDict([('Year', y)] + [(k, 0.0) for k in header])

            for k in header:
                row[k] = 0.0

            for topaz_id in data:
                for k in header:
                    row[k] += data[topaz_id][k][y] * 0.001 * areas[topaz_id]

            for k in header:
                row[k] /= wsarea
                row[k] *= 1000.0

            yield RowData(row)

    @property
    def avg_annual_header(self):
        return ['TopazID'] + list(self.hdr)

    @property
    def avg_annual_units(self):
        return [None] + list(self.units)

    def avg_annual_iter(self):
        data = self.data
        header = self.header

        num_water_years = len(self.years)

        for topaz_id in data:
            row = OrderedDict([('TopazID', topaz_id)])
            for k in header:
                row[k] = np.sum(list(data[topaz_id][k].values())) / (num_water_years - 1)

            yield RowData(row)


if __name__ == "__main__":
    #output_dir = '/geodata/weppcloud_runs/Blackwood_forStats/'
    output_dir = '/geodata/weppcloud_runs/1fa2e981-49b2-475a-a0dd-47f28b52c179/'
    watbal = HillslopeWatbal(output_dir)
    from pprint import pprint


    print(list(watbal.hdr))
    print(list(watbal.units))
    for row in watbal.yearly_iter():
#    for row in watbal.avg_annual_iter():
#    for row in watbal.daily_iter():
        print([(k, v) for k, v in row])

