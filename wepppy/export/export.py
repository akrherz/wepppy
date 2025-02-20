# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.


# standard-library
import os
import shutil

from os.path import join as _join
from os.path import exists as _exists
import shutil


# non-standard
from jinja2 import Template

import wepppy
from wepppy.wepp.management import _management_dir


#
# export
#
 
_thisdir = os.path.dirname(__file__)
_template_dir = _join(_thisdir, "templates")


def ww2_prw_template_loader():
    fn = _join(_template_dir, "ww2.prw.template")
    with open(fn) as fp:
        return fp.read()


def export_winwepp(wd):
    ron = wepppy.nodb.Watershed.getInstance(wd)
    
    export_dir = ron.export_dir
    export_winwepp_dir = ron.export_winwepp_dir
    
    if not _exists(export_dir):
        os.mkdir(export_dir)
        
    if _exists(export_winwepp_dir):
        shutil.rmtree(export_winwepp_dir)
    os.mkdir(export_winwepp_dir)
            
    ron = wepppy.nodb.Ron.getInstance(wd)
    watershed = wepppy.nodb.Watershed.getInstance(wd)
    climate = wepppy.nodb.Climate.getInstance(wd)
    landuse = wepppy.nodb.Landuse.getInstance(wd)
    soils = wepppy.nodb.Soils.getInstance(wd)
    translator = watershed.translator_factory()   
    
    template = Template(ww2_prw_template_loader())
    ww2 = template.render(ron=ron,
                          watershed=watershed,
                          climate=climate,
                          landuse=landuse,
                          soils=soils,
                          translator=translator,
                          impoundment_defs='')

    ww2 = ww2.split('\n')
    ww2 = '\n'.join(L for L in ww2 if L != '')
 
    os.mkdir(_join(export_winwepp_dir, 'projects'))
    with open(_join(export_winwepp_dir, 
                           'projects', 
                           'ww2.prw'), 'w') as fp:
        fp.write(ww2)
    
    shutil.copytree(ron.soils_dir,
                    _join(export_winwepp_dir, 'wepppy.nodb.Soils'))
                    
    shutil.copytree(_management_dir,
                    _join(export_winwepp_dir, 'managements'))
                    
    cligen_dir = _join(export_winwepp_dir, 'climates', 'cligen')
    shutil.copytree(ron.cli_dir, cligen_dir)
    with open(_join(cligen_dir, 'temp.par'), 'w') as fp:
        fp.write("don't beep")
                    
    with open(_join(cligen_dir, 'countries.txt'), 'w') as fp:
        fp.write("no beeping")

    export_winwepp_path = _join(export_dir, '{}_winwepp'.format(wd))
    shutil.make_archive(export_winwepp_path,
                        'zip', export_winwepp_dir)

    return export_winwepp_path + '.zip'


def archive_project(wd):
    archive_path = wd
    if archive_path.endswith('/') or archive_path.endswith('\\'):
        archive_path = archive_path[:-1]

    _zip_fn = archive_path + '.zip'

    if _exists(_zip_fn):
        os.remove(_zip_fn)

    shutil.make_archive(archive_path, 'zip', wd)

    return _zip_fn
