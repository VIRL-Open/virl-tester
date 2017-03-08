from virltester.virltester import loadCfg, doAllSims
from nose.tools import assert_equals
import logging

l = logging.getLogger()

def test_iosv_single():
    cfg = loadCfg('WORKDIR/iosv-single-test.yml')
    cfg['_workdir'] = 'WORKDIR'
    assert_equals(doAllSims(cfg, l), True)


