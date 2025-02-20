import os
import sys
from datetime import date

import shutil
from os.path import exists as _exists
from os.path import split as _split
from time import sleep
from copy import deepcopy

from wepppy.nodb.mods.locations.lt.selectors import *
from wepppy.all_your_base import isfloat
from wepppy.nodb import (
    Ron, Topaz, Watershed, Landuse, Soils, Climate, Wepp, SoilsMode, ClimateMode, ClimateSpatialMode, LanduseMode
)
from wepppy.nodb.mods.locations import SeattleMod

from wepppy.wepp.soils.utils import modify_kslast
from os.path import join as _join
from wepppy.wepp.out import TotalWatSed
from wepppy.export import arc_export

from wepppy.climates.cligen import ClimateFile

from osgeo import gdal

gdal.UseExceptions()

from wepppy._scripts.utils import *

os.chdir('/geodata/weppcloud_runs/')

wd = None


def log_print(*msg):
    now = datetime.now()
    print('[{now}] {wd}: {msg}'.format(now=now, wd=wd, msg=', '.join(str(v) for v in msg)))


if __name__ == '__main__':

    precip_transforms = {
        'gridmet': {
            'Cedar_River': 1,
            'Tolt_NorthFork': 1,
            'Taylor_Creek': 1
        },
        'daymet': {
            'Cedar_River': 1,
            'Tolt_NorthFork': 1,
            'Taylor_Creek': 1
        }
    }


    def _daymet_cli_adjust(cli_dir, cli_fn, watershed):
        cli = ClimateFile(_join(cli_dir, cli_fn))

        cli.discontinuous_temperature_adjustment(date(2005, 11, 2))

        pp_scale = precip_transforms['daymet'][watershed]
        cli.transform_precip(offset=0, scale=pp_scale)

        cli.write(_join(cli_dir, 'adj_' + cli_fn))

        return 'adj_' + cli_fn


    def _gridmet_cli_adjust(cli_dir, cli_fn, watershed):
        cli = ClimateFile(_join(cli_dir, cli_fn))

        pp_scale = precip_transforms['gridmet'][watershed]
        cli.transform_precip(offset=0, scale=pp_scale)

        cli.write(_join(cli_dir, 'adj_' + cli_fn))

        return 'adj_' + cli_fn

    watersheds = [
        dict(watershed='Cedar_River',
             extent=[-121.77108764648439, 47.163108130899104, -121.29043579101564, 47.4889049944156],
             map_center = [-121.49574279785158, 47.277365616965646],
             map_zoom = 11,
             outlet = [-121.62271296763015, 47.36246108025578],
             landuse=None,
             cs=200, erod=0.000001,
             csa=10, mcl=100,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.75, ksat=0.05),
        #dict(watershed='Tolt_NorthFork',
        #     extent=[-121.90086364746095, 47.56216409801383, -121.4202117919922, 47.88549944643875],
        #     map_center=[-121.66053771972658, 47.72408264363561],
        #     map_zoom=11,
        #     outlet=[-121.78852559978455, 47.71242486609417],
        #     landuse=None,
        #     cs=100, erod=0.000001,
        #     csa=10, mcl=100,
        #     surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
        #     gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
        #     mid_season_crop_coeff=0.95, p_coeff=0.75, ksat=0.0999),
        dict(watershed='Taylor_Creek',
             extent=[-121.8981170654297, 47.26199018174824, -121.65779113769533, 47.424835479167825],
             map_center=[-121.77795410156251, 47.34347562236255],
             map_zoom=11,
             outlet=[-121.84644704748708, 47.386266378562375],
             landuse=None,
             cs=100, erod=0.000001,
             csa=10, mcl=100,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=1.2, p_coeff=0.75, ksat=0.15)
              ]
    scenarios = [
        dict(wd='CurCond.202009.cl532.chn_cs{cs}',
             landuse=None,
             cli_mode='PRISMadj', clean=True, build_soils=True, build_landuse=True, build_climates=True,
             lc_lookup_fn='landSoilLookup.csv'),
        dict(wd='CurCond.202009.cl532_gridmet.chn_cs{cs}',
             landuse=None,
             cli_mode='observed', clean=True, build_soils=True, build_landuse=True, build_climates=True,
             lc_lookup_fn='landSoilLookup.csv'),
        dict(wd='CurCond.202009.cl532_future.chn_cs{cs}',
             landuse=None,
             cli_mode='future', clean=True, build_soils=True, build_landuse=True, build_climates=True,
             lc_lookup_fn='landSoilLookup.csv'),
        dict(wd='SimFire_Eagle.202009.cl532.chn_cs{cs}',
             landuse=None,
             cfg='seattle-simfire-eagle-snow',
             cli_mode='PRISMadj', clean=True, build_soils=True, build_landuse=True, build_climates=True,
             lc_lookup_fn='landSoilLookup.csv'),
        dict(wd='SimFire_Norse.202009.cl532.chn_cs{cs}',
             landuse=None,
             cfg='seattle-simfire-norse-snow',
             cli_mode='PRISMadj', clean=True, build_soils=True, build_landuse=True, build_climates=True,
             lc_lookup_fn='landSoilLookup.csv'),
        dict(wd='PrescFireS.202009.chn_cs{cs}',
             landuse=[(not_shrub_selector, 110), (shrub_selector, 122)],
             cli_mode='PRISMadj', clean=True, build_soils=True, build_landuse=True, build_climates=True,
             lc_lookup_fn='landSoilLookup.csv'),
        dict(wd='LowSevS.202009.chn_cs{cs}',
             landuse=[(not_shrub_selector, 106), (shrub_selector, 121)],
             cli_mode='PRISMadj', clean=True, build_soils=True, build_landuse=True, build_climates=True,
             lc_lookup_fn='landSoilLookup.csv'),
        dict(wd='ModSevS.202009.chn_cs{cs}',
             landuse=[(not_shrub_selector, 118), (shrub_selector, 120)],
             cli_mode='PRISMadj', clean=True, build_soils=True, build_landuse=True, build_climates=True,
             lc_lookup_fn='landSoilLookup.csv'),
        dict(wd='HighSevS.202009.chn_cs{cs}',
             landuse=[(not_shrub_selector, 105), (shrub_selector, 119)],
             cli_mode='PRISMadj', clean=True, build_soils=True, build_landuse=True, build_climates=True,
             lc_lookup_fn='landSoilLookup.csv'),
    ]

    wc = sys.argv[-1]
    if '.py' in wc:
        wc = None

    projects = []
    for scenario in scenarios:
        for watershed in watersheds:
            projects.append(deepcopy(watershed))
            
            projects[-1]['cfg'] = scenario.get('cfg', 'seattle-snow')
            projects[-1]['landuse'] = scenario['landuse']
            projects[-1]['cli_mode'] = scenario.get('cli_mode', 'observed')
            projects[-1]['clean'] = scenario['clean']
            projects[-1]['build_soils'] = scenario['build_soils']
            projects[-1]['build_landuse'] = scenario['build_landuse']
            projects[-1]['build_climates'] = scenario['build_climates']
            projects[-1]['lc_lookup_fn'] = scenario['lc_lookup_fn']
            projects[-1]['wd'] = 'seattle_k_{watershed}_{scenario}' \
                .format(watershed=watershed['watershed'], scenario=scenario['wd']) \
                .format(cs=watershed['cs'])

    for proj in projects:
        config = proj['cfg']
        watershed_name = proj['watershed']
        wd = proj['wd']
        ksat = proj['ksat']

        log_print(wd)
        if wc is not None:
            if not wc in wd:
                continue

        extent = proj['extent']
        map_center = proj['map_center']
        map_zoom = proj['map_zoom']
        outlet = proj['outlet']
        default_landuse = proj['landuse']
        cli_mode = proj['cli_mode']

        csa = proj['csa']
        mcl = proj['mcl']
        cs = proj['cs']
        erod = proj['erod']
        lc_lookup_fn = proj['lc_lookup_fn']

        clean = proj['clean']
        build_soils = proj['build_soils']
        build_landuse = proj['build_landuse']
        build_climates = proj['build_climates']

        if clean:
            if _exists(wd):
                shutil.rmtree(wd)
            os.mkdir(wd)

            ron = Ron(wd, config + '.cfg')
            ron.name = wd
            ron.set_map(extent, map_center, zoom=map_zoom)
            ron.fetch_dem()

            log_print('building channels')
            topaz = Topaz.getInstance(wd)
            topaz.build_channels(csa=csa, mcl=mcl)
            topaz.set_outlet(*outlet)
            sleep(0.5)

            log_print('building subcatchments')
            topaz.build_subcatchments()

            log_print('abstracting watershed')
            watershed = Watershed.getInstance(wd)
            watershed.abstract_watershed()
            translator = watershed.translator_factory()
            topaz_ids = [top.split('_')[1] for top in translator.iter_sub_ids()]

        else:
            ron = Ron.getInstance(wd)
            topaz = Topaz.getInstance(wd)
            watershed = Watershed.getInstance(wd)

        landuse = Landuse.getInstance(wd)
        if build_landuse:
            landuse.mode = LanduseMode.Gridded
            landuse.build()

        soils = Soils.getInstance(wd)
        if build_soils:
            log_print('building soils')
            soils.mode = SoilsMode.Gridded
            soils.build() 
            #soils.build_statsgo()

        climate = Climate.getInstance(wd)
        if build_climates:
            log_print('building climate')

        if cli_mode == 'observed':
            log_print('building observed')
            if 'daymet' in wd:
                stations = climate.find_closest_stations()
                climate.climatestation = stations[0]['id']

                climate.climate_mode = ClimateMode.Observed
                climate.climate_spatialmode = ClimateSpatialMode.Multiple
                climate.set_observed_pars(start_year=1990, end_year=2017)

                climate.build(verbose=1)

            elif 'gridmet' in wd:
                log_print('building gridmet')
                stations = climate.find_closest_stations()
                climate.climatestation = stations[0]['id']

                climate.climate_mode = ClimateMode.GridMetPRISM
                climate.climate_spatialmode = ClimateSpatialMode.Multiple
                climate.set_observed_pars(start_year=1980, end_year=2019)

                climate.build(verbose=1)

        elif cli_mode == 'future':
            log_print('building gridmet')
            stations = climate.find_closest_stations()
            climate.climatestation = stations[0]['id']

            climate.climate_mode = ClimateMode.Future
            climate.climate_spatialmode = ClimateSpatialMode.Multiple
            climate.set_future_pars(start_year=2006, end_year=2099)

            climate.build(verbose=1)

        elif cli_mode == 'PRISMadj':
            stations = climate.find_closest_stations()
            climate.climatestation = stations[0]['id']

            log_print('climate_station:', climate.climatestation)

            climate.climate_mode = ClimateMode.PRISM
            climate.climate_spatialmode = ClimateSpatialMode.Multiple
            climate.input_years = 100

            climate.build(verbose=1)

        elif cli_mode == 'vanilla':
            stations = climate.find_closest_stations()
            climate.climatestation = stations[0]['id']

            log_print('climate_station:', climate.climatestation)

            climate.climate_mode = ClimateMode.Vanilla
            climate.climate_spatialmode = ClimateSpatialMode.Single
            climate.input_years = 100

            climate.build(verbose=1)

        log_print('running wepp')
        wepp = Wepp.getInstance(wd)
        wepp.parse_inputs(proj)

        wepp.prep_hillslopes()

        log_print('running hillslopes')
        wepp.run_hillslopes()

        wepp = Wepp.getInstance(wd)
        wepp.prep_watershed(erodibility=erod, critical_shear=cs)
        wepp._prep_pmet(mid_season_crop_coeff=proj['mid_season_crop_coeff'], p_coeff=proj['p_coeff'])
        wepp.run_watershed()
        loss_report = wepp.report_loss()

        log_print('running wepppost')
        fn = _join(ron.export_dir, 'totalwatsed.csv')

        totwatsed = TotalWatSed(_join(ron.output_dir, 'totalwatsed.txt'),
                                wepp.baseflow_opts, wepp.phosphorus_opts)
        totwatsed.export(fn)
        assert _exists(fn)

        arc_export(wd)
