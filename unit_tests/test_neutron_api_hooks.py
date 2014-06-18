from mock import MagicMock, patch, call
from test_utils import CharmTestCase


with patch('charmhelpers.core.hookenv.config') as config:
    config.return_value = 'neutron'
    import neutron_api_utils as utils

_reg = utils.register_configs
_map = utils.restart_map

utils.register_configs = MagicMock()
utils.restart_map = MagicMock()

import neutron_api_hooks as hooks

utils.register_configs = _reg
utils.restart_map = _map

TO_PATCH = [
    'api_port',
    'apt_update',
    'apt_install',
#    'charm_dir',
    'canonical_url',
    'config',
    'CONFIGS',
    'configure_installation_source',
    'determine_endpoints',
    'determine_packages',
    'determine_ports',
    'execd_preinstall',
    'is_leader',
    'is_relation_made',
    'log',
    'network_manager',
    'open_port',
    'relation_get',
    'relation_ids',
    'relation_set',
    'related_units',
    'unit_get',
]
NEUTRON_CONF_DIR = "/etc/neutron"

NEUTRON_CONF = '%s/neutron.conf' % NEUTRON_CONF_DIR

from random import randrange

class NeutronAPIHooksTests(CharmTestCase):

    def setUp(self):
        super(NeutronAPIHooksTests, self).setUp(hooks, TO_PATCH)

        self.config.side_effect = self.test_config.get
        self.relation_get.side_effect = self.test_relation.get
        self.test_config.set('openstack-origin', 'distro')
        self.test_config.set('neutron-plugin', 'ovs')
#        self.test_config.set('neutron-external-network', 'ext_net')
#        self.lsb_release.return_value = {'DISTRIB_CODENAME': 'trusty'}
#        self.charm_dir.return_value = '/var/lib/juju/charms/neutron/charm'

    def _fake_relids(self, rel_name):
        return [ randrange(100) for _count in range(2) ]

    def _call_hook(self, hookname):
        hooks.hooks.execute([
            'hooks/{}'.format(hookname)])

    def test_install_hook(self):
        _pkgs = ['foo', 'bar']
        _ports = [80, 81, 82]
        _port_calls = [ call(port) for port in _ports ]
        self.determine_packages.return_value = _pkgs
        self.determine_ports.return_value = _ports
        self._call_hook('install')
        self.configure_installation_source.assert_called_with(
            'distro'
        )
        self.apt_update.assert_called_with()
        self.apt_install.assert_has_calls([
            call(_pkgs, fatal=True),
        ])
        self.open_port.assert_has_calls(_port_calls)
        self.assertTrue(self.execd_preinstall.called)

    def test_config_changed(self):
        self.relation_ids.side_effect = self._fake_relids
        _n_api_rel_joined = self.patch('neutron_api_relation_joined')
        _n_plugin_api_rel_joined = self.patch('neutron_plugin_api_relation_joined')
        _amqp_rel_joined = self.patch('amqp_joined')
        _id_rel_joined = self.patch('identity_joined')
        self._call_hook('config-changed')
        self.assertTrue(_n_api_rel_joined.called)
        self.assertTrue(_n_plugin_api_rel_joined.called)
        self.assertTrue(_amqp_rel_joined.called)
        self.assertTrue(_id_rel_joined.called)
        self.assertTrue(self.CONFIGS.write_all.called)

    def test_amqp_joined(self):
        self._call_hook('amqp-relation-joined')
        self.relation_set.assert_called_with(
            username='neutron',
            vhost='openstack',
            relation_id=None
        )

    def test_amqp_changed(self):
        self.CONFIGS.complete_contexts.return_value = ['amqp']
        self._call_hook('amqp-relation-changed')
        self.assertTrue(self.CONFIGS.write.called_with(NEUTRON_CONF))

    def test_amqp_departed(self):
        self._call_hook('amqp-relation-departed')
        self.assertTrue(self.CONFIGS.write.called_with(NEUTRON_CONF))

    def test_db_joined(self):
        self.is_relation_made.return_value = False
        self.unit_get.return_value = 'myhostname'
        self._call_hook('shared-db-relation-joined')
        self.relation_set.assert_called_with(
            username='neutron',
            database='neutron',
            hostname='myhostname',
        )

    def test_db_joined_with_postgresql(self):
        self.is_relation_made.return_value = True

        with self.assertRaises(Exception) as context:
            hooks.db_joined()
        self.assertEqual(context.exception.message,
                         'Attempting to associate a mysql database when there '
                         'is already associated a postgresql one')

    def test_postgresql_db_joined(self):
        self.unit_get.return_value = 'myhostname'
        self.is_relation_made.return_value = False
        self._call_hook('pgsql-db-relation-joined')
        self.relation_set.assert_called_with(
            database='neutron',
        )

    def test_postgresql_joined_with_db(self):
        self.is_relation_made.return_value = True

        with self.assertRaises(Exception) as context:
            hooks.pgsql_neutron_db_joined()
        self.assertEqual(context.exception.message,
                         'Attempting to associate a postgresql database when'
                         ' there is already associated a mysql one')

    def test_shared_db_changed(self):
        self.CONFIGS.complete_contexts.return_value = ['shared-db']
        self._call_hook('shared-db-relation-changed')
        self.assertTrue(self.CONFIGS.write_all.called)

    def test_shared_db_changed_partial_ctxt(self):
        self.CONFIGS.complete_contexts.return_value = []
        self._call_hook('shared-db-relation-changed')
        self.assertFalse(self.CONFIGS.write_all.called)

    def test_pgsql_db_changed(self):
        self.network_manager.return_value = 'neutron'
        self._call_hook('pgsql-db-relation-changed')
        self.assertTrue(self.CONFIGS.write.called)

    def test_amqp_broken(self):
        self._call_hook('amqp-relation-broken')
        self.assertTrue(self.CONFIGS.write_all.called)

    def test_identity_joined(self):
        _neutron_url = 'http://127.0.0.1:1234'
        _endpoints = {
            'quantum_service': 'quantum',
            'quantum_region': 'region1',
            'quantum_public_url': _neutron_url,
            'quantum_admin_url': _neutron_url,
            'quantum_internal_url': _neutron_url,
        }
        self.determine_endpoints.return_value = _endpoints
        self._call_hook('identity-service-relation-joined')
        self.relation_set.assert_called_with(
            relation_id=None,
            **_endpoints
        )

    def test_identity_changed_partial_ctxt(self):
        self.CONFIGS.complete_contexts.return_value = []
        _api_rel_joined = self.patch('neutron_api_relation_joined')
        self.relation_ids.side_effect = self._fake_relids
        self._call_hook('identity-service-relation-changed')
        self.assertFalse(_api_rel_joined.called)

    def test_identity_changed(self):
        self.CONFIGS.complete_contexts.return_value = ['identity-service']
        _api_rel_joined = self.patch('neutron_api_relation_joined')
        self.relation_ids.side_effect = self._fake_relids
        self._call_hook('identity-service-relation-changed')
        self.assertTrue(self.CONFIGS.write.called_with(NEUTRON_CONF))
        self.assertTrue(_api_rel_joined.called)
          
    @patch.object(hooks, '_get_keystone_info')
    def test_neutron_api_relation_no_id_joined(self, _get_ks_info):
        _get_ks_info.return_value = None
        manager = 'neutron'
        host = 'http://127.0.0.1'
        port = 1234
        _id_rel_joined = self.patch('identity_joined')
        self.relation_ids.side_effect = self._fake_relids
        self.network_manager.return_value = manager
        self.canonical_url.return_value = host
        self.api_port.return_value = port
        self.is_relation_made = False
        neutron_url = '%s:%s' % (host, port)
        _relation_data = {
            'network_manager': manager,
            'default_floating_pool': 'ext_net',
            'external_network': 'ext_net',
            manager + '_plugin': 'ovs',
            manager + '_url': neutron_url,
            'neutron_security_groups': 'no',
        }
        self._call_hook('neutron-api-relation-joined')
        self.relation_set.assert_called_with(
            relation_id=None,
            **_relation_data
        )
        self.assertTrue(_id_rel_joined.called)
        self.test_config.set('neutron-security-groups', True)
        self._call_hook('neutron-api-relation-joined')
        _relation_data['neutron_security_groups'] = 'yes'
        self.relation_set.assert_called_with(
            relation_id=None,
            **_relation_data
        )

    @patch.object(hooks, '_get_keystone_info')
    def test_neutron_api_relation_joined(self, _get_ks_info):
        _ks_info = {
             'service_tenant': 'bob',
             'service_username': 'bob',
             'service_password': 'bob',
             'auth_url': 'http://127.0.0.2',
        } 
        _get_ks_info.return_value = _ks_info
        manager = 'neutron'
        host = 'http://127.0.0.1'
        port = 1234
        self.network_manager.return_value = manager
        self.canonical_url.return_value = host
        self.api_port.return_value = port
        self.is_relation_made = True
        neutron_url = '%s:%s' % (host, port)
        _relation_data = {
            'network_manager': manager,
            'default_floating_pool': 'ext_net',
            'external_network': 'ext_net',
            manager + '_plugin': 'ovs',
            manager + '_url': neutron_url,
            'neutron_security_groups': 'no',
            manager + '_admin_tenant_name': _ks_info['service_tenant'],
            manager + '_admin_username': _ks_info['service_username'],
            manager + '_admin_password': _ks_info['service_password'],
            manager + '_admin_auth_url': _ks_info['auth_url'],
        }
        self._call_hook('neutron-api-relation-joined')
        self.relation_set.assert_called_with(
            relation_id=None,
            **_relation_data
        )

    def test_neutron_api_relation_changed(self):
        self._call_hook('neutron-api-relation-changed')
        self.assertTrue(self.CONFIGS.write.called_with(NEUTRON_CONF))

    def test_neutron_plugin_api_relation_joined(self):
        _relation_data = {
            'neutron_security_groups': False,
        }
        self._call_hook('neutron-plugin-api-relation-joined')
        self.relation_set.assert_called_with(
            relation_id=None,
            **_relation_data
        )

    def test_cluster_changed(self):
        self._call_hook('cluster-relation-changed')
        self.assertTrue(self.CONFIGS.write_all.called)

    @patch.object(hooks, 'get_hacluster_config')
    def test_ha_joined(self, _get_ha_config):
        _ha_config = {
             'vip': '10.0.0.1',
             'vip_cidr': '24',
             'vip_iface': 'eth0',
             'ha-bindiface': 'eth1',
             'ha-mcastport': '5405',
        } 
        vip_params = 'params ip="%s" cidr_netmask="%s" nic="%s"' % \
                     (_ha_config['vip'], _ha_config['vip_cidr'], _ha_config['vip_iface'])
        
        _get_ha_config.return_value = _ha_config
        _relation_data = {
            'init_services': {'res_neutron_haproxy': 'haproxy'},
            'corosync_bindiface': _ha_config['ha-bindiface'],
            'corosync_mcastport': _ha_config['ha-mcastport'],
            'resources': {'res_neutron_vip': 'ocf:heartbeat:IPaddr2',
                          'res_neutron_haproxy': 'lsb:haproxy'},
            'resource_params': { 'res_neutron_vip': vip_params,
                                 'res_neutron_haproxy': 'op monitor interval="5s"'},
            'clones': { 'cl_nova_haproxy': 'res_neutron_haproxy' }
        }
        self._call_hook('ha-relation-joined')
        self.relation_set.assert_called_with(
            **_relation_data
        )

    def test_ha_changed(self):
        self.test_relation.set({
            'clustered': 'true',
        })
        self.is_leader.return_value = True
        self.relation_ids.side_effect = self._fake_relids
        _n_api_rel_joined = self.patch('neutron_api_relation_joined')
        _id_rel_joined = self.patch('identity_joined')
        self._call_hook('ha-relation-changed')
        self.assertTrue(_n_api_rel_joined.called)
        self.assertTrue(_id_rel_joined.called)

    def test_ha_changed_not_leader(self):
        self.test_relation.set({
            'clustered': 'true',
        })
        self.is_leader.return_value = False
        self.relation_ids.side_effect = self._fake_relids
        _n_api_rel_joined = self.patch('neutron_api_relation_joined')
        _id_rel_joined = self.patch('identity_joined')
        self._call_hook('ha-relation-changed')
        self.assertFalse(_n_api_rel_joined.called)
        self.assertFalse(_id_rel_joined.called)

    def test_ha_changed_not_clustered(self):
        self.test_relation.set({
            'clustered': None,
        })
        self.is_leader.return_value = False
        self.relation_ids.side_effect = self._fake_relids
        _n_api_rel_joined = self.patch('neutron_api_relation_joined')
        _id_rel_joined = self.patch('identity_joined')
        self._call_hook('ha-relation-changed')
        self.assertFalse(_n_api_rel_joined.called)
        self.assertFalse(_id_rel_joined.called)

    def test_get_keystone_info(self):
        self.relation_ids.return_value = 'relid1'
        self.related_units.return_value = 'unit1'
        _ks_info = {
            'service_protocol': 'https',
            'service_host': '127.0.0.3',
            'service_port': '4567',
            'service_tenant': 'region12',
            'service_username': 'bob',
            'service_password': 'pass',
        }
        self.test_relation.set(_ks_info)
        auth_url = "%s://%s:%s/v2.0" % (_ks_info['service_protocol'],
                                        _ks_info['service_host'],
                                        _ks_info['service_port'])
        expect_ks_info = {
            'service_protocol': _ks_info['service_protocol'],
            'service_host': _ks_info['service_host'],
            'service_port': _ks_info['service_port'],
            'service_tenant': _ks_info['service_tenant'],
            'service_username': _ks_info['service_username'],
            'service_password': _ks_info['service_password'],
            'auth_url': auth_url,
        }
        self.assertEqual(hooks._get_keystone_info(), expect_ks_info)
