"basic smoke test using nose tests"
import logging

from virltester.tester import do_all_sims, load_cfg

from nose.tools import assert_equals

l = logging.getLogger()

def test_iosv_single():
    "test a single sim"
    cfg = load_cfg('Examples/iosv.yml')
    cfg['_workdir'] = 'Examples'
    assert_equals(do_all_sims(cfg, l), True)
