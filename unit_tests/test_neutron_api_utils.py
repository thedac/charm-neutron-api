
from mock import MagicMock, call, patch
from collections import OrderedDict
import charmhelpers.contrib.openstack.templating as templating

templating.OSConfigRenderer = MagicMock()

import neutron_api_utils as nutils

from test_utils import (
    CharmTestCase,
    patch_open,
)

import charmhelpers.core.hookenv as hookenv


TO_PATCH = [
    'b64encode',
    'config',
#    'neutron_plugin_attribute',
]


class TestNeutronAPIUtils(CharmTestCase):

    def setUp(self):
        super(TestNeutronAPIUtils, self).setUp(nutils, TO_PATCH)
        self.config.side_effect = self.test_config.get
        self.test_config.set('region', 'region101')

    def tearDown(self):
        # Reset cached cache
        hookenv.cache = {}

    def test_api_port(self):
        port = nutils.api_port('neutron-server')
        self.assertEqual(port, nutils.API_PORTS['neutron-server'])

    def test_determine_endpoints(self):
        test_url = 'http://127.0.0.1'
        endpoints = nutils.determine_endpoints(test_url)
        neutron_url = '%s:%s' % (test_url,
                                 nutils.api_port('neutron-server')) 
        expect = {
            'quantum_service': 'quantum',
            'quantum_region': 'region101',
            'quantum_public_url': neutron_url,
            'quantum_admin_url': neutron_url,
            'quantum_internal_url': neutron_url,
        }
        self.assertEqual(endpoints, expect)

    def test_determine_packages(self):
        pkg_list = nutils.determine_packages()
        expect = nutils.BASE_PACKAGES
        expect.extend(['neutron-server', 'neutron-plugin-ml2'])
        self.assertItemsEqual(pkg_list, expect)

    def test_determine_ports(self):
        port_list = nutils.determine_ports()
        self.assertItemsEqual(port_list, [9696])

    def test_resource_map(self):
        _map = nutils.resource_map()
        confs = [nutils.NEUTRON_CONF, nutils.NEUTRON_DEFAULT]
        [self.assertIn(q_conf, _map.keys()) for q_conf in confs]

    def test_restart_map(self):
        _restart_map = nutils.restart_map()
        ML2CONF = "/etc/neutron/plugins/ml2/ml2_conf.ini"
        expect = OrderedDict([
            (nutils.NEUTRON_CONF, {
                'services': ['neutron-server'],
            }),
            (nutils.NEUTRON_DEFAULT, {
                'services': ['neutron-server'],
            }),
            (ML2CONF, {
                'services': ['neutron-server'],
            }),
        ])
        self.assertItemsEqual(_restart_map, expect)

    def test_register_configs(self):
        class _mock_OSConfigRenderer():
            def __init__(self, templates_dir=None, openstack_release=None):
                self.configs = []
                self.ctxts = []

            def register(self, config, ctxt):
                self.configs.append(config)
                self.ctxts.append(ctxt)

        templating.OSConfigRenderer.side_effect = _mock_OSConfigRenderer
        _regconfs = nutils.register_configs()
        confs = ['/etc/neutron/neutron.conf',
                 '/etc/default/neutron-server',
                 '/etc/neutron/plugins/ml2/ml2_conf.ini']
        self.assertItemsEqual(_regconfs.configs, confs)

    @patch('os.path.isfile')
    def test_keystone_ca_cert_b64_no_cert_file(self, _isfile):
        _isfile.return_value = False
        cert = nutils.keystone_ca_cert_b64()
        self.assertEquals(cert, None)

    @patch('os.path.isfile')
    def test_keystone_ca_cert_b64(self, _isfile):
        _isfile.return_value = True
        with patch_open() as (_open, _file):
            cert = nutils.keystone_ca_cert_b64()
            self.assertTrue(self.b64encode.called)
