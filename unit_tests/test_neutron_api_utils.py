
from mock import MagicMock, patch, call
from collections import OrderedDict
from copy import deepcopy
import charmhelpers.contrib.openstack.templating as templating

templating.OSConfigRenderer = MagicMock()

with patch('charmhelpers.core.hookenv.config') as config:
    config.return_value = 'neutron'
    import neutron_api_utils as nutils

from test_utils import (
    CharmTestCase,
    patch_open,
)

import charmhelpers.core.hookenv as hookenv


TO_PATCH = [
    'apt_install',
    'apt_update',
    'apt_upgrade',
    'b64encode',
    'config',
    'configure_installation_source',
    'get_os_codename_install_source',
    'log',
    'neutron_plugin_attribute',
    'os_release',
]

openstack_origin_git = \
    """repositories:
         - {name: requirements,
            repository: 'git://git.openstack.org/openstack/requirements',
            branch: stable/juno}
         - {name: neutron,
            repository: 'git://git.openstack.org/openstack/neutron',
            branch: stable/juno}"""


def _mock_npa(plugin, attr, net_manager=None):
    plugins = {
        'ovs': {
            'config': '/etc/neutron/plugins/ml2/ml2_conf.ini',
            'driver': 'neutron.plugins.ml2.plugin.Ml2Plugin',
            'contexts': [],
            'services': ['neutron-plugin-openvswitch-agent'],
            'packages': [['neutron-plugin-openvswitch-agent']],
            'server_packages': ['neutron-server',
                                'neutron-plugin-ml2'],
            'server_services': ['neutron-server']
        },
    }
    return plugins[plugin][attr]


class TestNeutronAPIUtils(CharmTestCase):
    def setUp(self):
        super(TestNeutronAPIUtils, self).setUp(nutils, TO_PATCH)
        self.config.side_effect = self.test_config.get
        self.test_config.set('region', 'region101')
        self.neutron_plugin_attribute.side_effect = _mock_npa
        self.os_release.side_effect = 'trusty'

    def tearDown(self):
        # Reset cached cache
        hookenv.cache = {}

    def test_api_port(self):
        port = nutils.api_port('neutron-server')
        self.assertEqual(port, nutils.API_PORTS['neutron-server'])

    @patch.object(nutils, 'git_install_requested')
    def test_determine_packages(self, git_requested):
        git_requested.return_value = False
        pkg_list = nutils.determine_packages()
        expect = deepcopy(nutils.BASE_PACKAGES)
        expect.extend(['neutron-server', 'neutron-plugin-ml2'])
        self.assertItemsEqual(pkg_list, expect)

    @patch.object(nutils, 'git_install_requested')
    def test_determine_packages_kilo(self, git_requested):
        git_requested.return_value = False
        self.get_os_codename_install_source.return_value = 'kilo'
        pkg_list = nutils.determine_packages()
        expect = deepcopy(nutils.BASE_PACKAGES)
        expect.extend(['neutron-server', 'neutron-plugin-ml2'])
        expect.extend(nutils.KILO_PACKAGES)
        self.assertItemsEqual(pkg_list, expect)

    def test_determine_ports(self):
        port_list = nutils.determine_ports()
        self.assertItemsEqual(port_list, [9696])

    @patch('os.path.exists')
    def test_resource_map(self, _path_exists):
        _path_exists.return_value = False
        _map = nutils.resource_map()
        confs = [nutils.NEUTRON_CONF, nutils.NEUTRON_DEFAULT,
                 nutils.APACHE_CONF]
        [self.assertIn(q_conf, _map.keys()) for q_conf in confs]
        self.assertTrue(nutils.APACHE_24_CONF not in _map.keys())

    @patch('os.path.exists')
    def test_resource_map_apache24(self, _path_exists):
        _path_exists.return_value = True
        _map = nutils.resource_map()
        confs = [nutils.NEUTRON_CONF, nutils.NEUTRON_DEFAULT,
                 nutils.APACHE_24_CONF]
        [self.assertIn(q_conf, _map.keys()) for q_conf in confs]
        self.assertTrue(nutils.APACHE_CONF not in _map.keys())

    @patch('os.path.exists')
    def test_restart_map(self, mock_path_exists):
        mock_path_exists.return_value = False
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
            (nutils.APACHE_CONF, {
                'services': ['apache2'],
            }),
            (nutils.HAPROXY_CONF, {
                'services': ['haproxy'],
            }),
        ])
        self.assertItemsEqual(_restart_map, expect)

    @patch('os.path.exists')
    def test_register_configs(self, mock_path_exists):
        mock_path_exists.return_value = False

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
                 '/etc/neutron/plugins/ml2/ml2_conf.ini',
                 '/etc/apache2/sites-available/openstack_https_frontend',
                 '/etc/haproxy/haproxy.cfg']
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
            nutils.keystone_ca_cert_b64()
            self.assertTrue(self.b64encode.called)

    @patch.object(nutils, 'git_install_requested')
    def test_do_openstack_upgrade(self, git_requested):
        git_requested.return_value = False
        self.config.side_effect = self.test_config.get
        self.test_config.set('openstack-origin', 'cloud:trusty-juno')
        self.os_release.side_effect = 'icehouse'
        self.get_os_codename_install_source.return_value = 'juno'
        configs = MagicMock()
        nutils.do_openstack_upgrade(configs)
        self.log.assert_called()
        self.configure_installation_source.assert_called_with(
            'cloud:trusty-juno'
        )
        self.apt_update.assert_called_with(fatal=True)
        dpkg_opts = [
            '--option', 'Dpkg::Options::=--force-confnew',
            '--option', 'Dpkg::Options::=--force-confdef',
        ]
        self.apt_upgrade.assert_called_with(options=dpkg_opts,
                                            fatal=True,
                                            dist=True)
        pkgs = nutils.determine_packages()
        pkgs.sort()
        self.apt_install.assert_called_with(packages=pkgs,
                                            options=dpkg_opts,
                                            fatal=True)
        configs.set_release.assert_called_with(openstack_release='juno')

    @patch.object(nutils, 'git_install_requested')
    @patch.object(nutils, 'git_clone_and_install')
    @patch.object(nutils, 'git_post_install')
    @patch.object(nutils, 'git_pre_install')
    def test_git_install(self, git_pre, git_post, git_clone_and_install,
                         git_requested):
        projects_yaml = openstack_origin_git
        git_requested.return_value = True
        nutils.git_install(projects_yaml)
        self.assertTrue(git_pre.called)
        git_clone_and_install.assert_called_with(openstack_origin_git,
                                                 core_project='neutron')
        self.assertTrue(git_post.called)

    @patch.object(nutils, 'mkdir')
    @patch.object(nutils, 'write_file')
    @patch.object(nutils, 'add_user_to_group')
    @patch.object(nutils, 'add_group')
    @patch.object(nutils, 'adduser')
    def test_git_pre_install(self, adduser, add_group, add_user_to_group,
                             write_file, mkdir):
        nutils.git_pre_install()
        adduser.assert_called_with('neutron', shell='/bin/bash',
                                   system_user=True)
        add_group.assert_called_with('neutron', system_group=True)
        add_user_to_group.assert_called_with('neutron', 'neutron')
        expected = [
            call('/var/lib/neutron', owner='neutron',
                 group='neutron', perms=0755, force=False),
            call('/var/lib/neutron/lock', owner='neutron',
                 group='neutron', perms=0755, force=False),
            call('/var/log/neutron', owner='neutron',
                 group='neutron', perms=0755, force=False),
        ]
        self.assertEquals(mkdir.call_args_list, expected)
        expected = [
            call('/var/log/neutron/server.log', '', owner='neutron',
                 group='neutron', perms=0600),
        ]
        self.assertEquals(write_file.call_args_list, expected)

    @patch.object(nutils, 'git_src_dir')
    @patch.object(nutils, 'service_restart')
    @patch.object(nutils, 'render')
    @patch('os.path.join')
    @patch('os.path.exists')
    @patch('shutil.copytree')
    @patch('shutil.rmtree')
    def test_git_post_install(self, rmtree, copytree, exists, join, render,
                              service_restart, git_src_dir):
        projects_yaml = openstack_origin_git
        join.return_value = 'joined-string'
        nutils.git_post_install(projects_yaml)
        expected = [
            call('joined-string', '/etc/neutron'),
            call('joined-string', '/etc/neutron/plugins'),
            call('joined-string', '/etc/neutron/rootwrap.d'),
        ]
        copytree.assert_has_calls(expected)
        neutron_api_context = {
            'service_description': 'Neutron API server',
            'charm_name': 'neutron-api',
            'process_name': 'neutron-server',
            'executable_name': 'joined-string',
        }
        expected = [
            call('git/neutron_sudoers', '/etc/sudoers.d/neutron_sudoers', {},
                 perms=0o440),
            call('git/upstart/neutron-server.upstart',
                 '/etc/init/neutron-server.conf',
                 neutron_api_context, perms=0o644),
        ]
        self.assertEquals(render.call_args_list, expected)
        expected = [
            call('neutron-server'),
        ]
        self.assertEquals(service_restart.call_args_list, expected)
