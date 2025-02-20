import os
from os.path import join as _join

from .wepp_runner import (
    make_hillslope_run,
    make_ss_hillslope_run,
    run_hillslope,
    make_flowpath_run,
    run_flowpath,
    make_watershed_run,
    make_ss_watershed_run,
    run_watershed
)

_thisdir = os.path.dirname(__file__)
