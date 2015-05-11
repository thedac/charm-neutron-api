#!/usr/bin/python

import amulet
import os
import yaml

from charmhelpers.contrib.openstack.amulet.deployment import (
    OpenStackAmuletDeployment
)

from charmhelpers.contrib.openstack.amulet.utils import (
    OpenStackAmuletUtils,
    DEBUG, # flake8: noqa
    ERROR
)

# Use DEBUG to turn on debug logging
u = OpenStackAmuletUtils(DEBUG)


class NeutronAPIBasicDeployment(OpenStackAmuletDeployment):
    """Amulet tests on a basic neutron-api deployment."""

    def __init__(self, series, openstack=None, source=None, git=False,
                 stable=False):
        """Deploy the entire test environment."""
        super(NeutronAPIBasicDeployment, self).__init__(series, openstack,
                                                        source, stable)
        self.git = git
        self._add_services()
        self._add_relations()
        self._configure_services()
        self._deploy()
        self._initialize_tests()

    def _add_services(self):
        """Add services

           Add the services that we're testing, where neutron-api is local,
           and the rest of the service are from lp branches that are
           compatible with the local charm (e.g. stable or next).
           """
        this_service = {'name': 'neutron-api'}
        other_services = [{'name': 'mysql'},
                          {'name': 'rabbitmq-server'}, {'name': 'keystone'},
                          {'name': 'neutron-openvswitch'},
                          {'name': 'nova-cloud-controller'},
                          {'name': 'quantum-gateway'},
                          {'name': 'nova-compute'}]
        super(NeutronAPIBasicDeployment, self)._add_services(this_service,
                                                             other_services)

    def _add_relations(self):
        """Add all of the relations for the services."""
        relations = {
            'neutron-api:shared-db': 'mysql:shared-db',
            'neutron-api:amqp': 'rabbitmq-server:amqp',
            'neutron-api:neutron-api': 'nova-cloud-controller:neutron-api',
            'neutron-api:neutron-plugin-api': 'quantum-gateway:'
                                              'neutron-plugin-api',
            'neutron-api:neutron-plugin-api': 'neutron-openvswitch:'
                                              'neutron-plugin-api',
            'neutron-api:identity-service': 'keystone:identity-service',
            'keystone:shared-db': 'mysql:shared-db',
            'nova-compute:neutron-plugin': 'neutron-openvswitch:neutron-plugin',
            'nova-cloud-controller:shared-db': 'mysql:shared-db',
        }
        super(NeutronAPIBasicDeployment, self)._add_relations(relations)

    def _configure_services(self):
        """Configure all of the services."""
        neutron_api_config = {}
        if self.git:
            branch = 'stable/' + self._get_openstack_release_string()
            amulet_http_proxy = os.environ.get('AMULET_HTTP_PROXY')
            openstack_origin_git = {
                'repositories': [
                    {'name': 'requirements',
                     'repository': 'git://git.openstack.org/openstack/requirements',
                     'branch': branch},
                    {'name': 'neutron',
                     'repository': 'git://git.openstack.org/openstack/neutron',
                     'branch': branch},
                ],
                'directory': '/mnt/openstack-git',
                'http_proxy': amulet_http_proxy,
                'https_proxy': amulet_http_proxy,
            }
            neutron_api_config['openstack-origin-git'] = yaml.dump(openstack_origin_git)
        keystone_config = {'admin-password': 'openstack',
                           'admin-token': 'ubuntutesting'}
        nova_cc_config = {'network-manager': 'Quantum',
                          'quantum-security-groups': 'yes'}
        configs = {'neutron-api': neutron_api_config,
                   'keystone': keystone_config,
                   'nova-cloud-controller': nova_cc_config}
        super(NeutronAPIBasicDeployment, self)._configure_services(configs)

    def _initialize_tests(self):
        """Perform final initialization before tests get run."""
        # Access the sentries for inspecting service units
        self.mysql_sentry = self.d.sentry.unit['mysql/0']
        self.keystone_sentry = self.d.sentry.unit['keystone/0']
        self.rabbitmq_sentry = self.d.sentry.unit['rabbitmq-server/0']
        self.nova_cc_sentry = self.d.sentry.unit['nova-cloud-controller/0']
        self.quantum_gateway_sentry = self.d.sentry.unit['quantum-gateway/0']
        self.neutron_api_sentry = self.d.sentry.unit['neutron-api/0']
        self.nova_compute_sentry = self.d.sentry.unit['nova-compute/0']
        u.log.debug('openstack release val: {}'.format(
            self._get_openstack_release()))
        u.log.debug('openstack release str: {}'.format(
            self._get_openstack_release_string()))

    def test_neutron_api_shared_db_relation(self):
        """Verify the neutron-api to mysql shared-db relation data"""
        unit = self.neutron_api_sentry
        relation = ['shared-db', 'mysql:shared-db']
        expected = {
            'private-address': u.valid_ip,
            'database': 'neutron',
            'username': 'neutron',
            'hostname': u.valid_ip
        }

        ret = u.validate_relation_data(unit, relation, expected)
        if ret:
            message = u.relation_error('neutron-api shared-db', ret)
            amulet.raise_status(amulet.FAIL, msg=message)

    def test_shared_db_neutron_api_relation(self):
        """Verify the mysql to neutron-api shared-db relation data"""
        unit = self.mysql_sentry
        relation = ['shared-db', 'neutron-api:shared-db']
        expected = {
            'db_host': u.valid_ip,
            'private-address': u.valid_ip,
        }

        if self._get_openstack_release() == self.precise_icehouse:
            # Precise
            expected['allowed_units'] = 'nova-cloud-controller/0 neutron-api/0'
        else:
            # Not Precise
            expected['allowed_units'] = 'neutron-api/0'

        ret = u.validate_relation_data(unit, relation, expected)
        rel_data = unit.relation('shared-db', 'neutron-api:shared-db')
        if ret or 'password' not in rel_data:
            message = u.relation_error('mysql shared-db', ret)
            amulet.raise_status(amulet.FAIL, msg=message)

    def test_neutron_api_amqp_relation(self):
        """Verify the neutron-api to rabbitmq-server amqp relation data"""
        unit = self.neutron_api_sentry
        relation = ['amqp', 'rabbitmq-server:amqp']
        expected = {
            'username': 'neutron',
            'private-address': u.valid_ip,
            'vhost': 'openstack'
        }

        ret = u.validate_relation_data(unit, relation, expected)
        if ret:
            message = u.relation_error('neutron-api amqp', ret)
            amulet.raise_status(amulet.FAIL, msg=message)

    def test_amqp_neutron_api_relation(self):
        """Verify the rabbitmq-server to neutron-api amqp relation data"""
        unit = self.rabbitmq_sentry
        relation = ['amqp', 'neutron-api:amqp']
        rel_data = unit.relation('amqp', 'neutron-api:amqp')
        expected = {
            'hostname': u.valid_ip,
            'private-address': u.valid_ip,
        }

        ret = u.validate_relation_data(unit, relation, expected)
        if ret or not 'password' in rel_data:
            message = u.relation_error('rabbitmq amqp', ret)
            amulet.raise_status(amulet.FAIL, msg=message)

    def test_neutron_api_identity_relation(self):
        """Verify the neutron-api to keystone identity-service relation data"""
        unit = self.neutron_api_sentry
        relation = ['identity-service', 'keystone:identity-service']
        api_ip = unit.relation('identity-service',
                               'keystone:identity-service')['private-address']
        api_endpoint = "http://%s:9696" % (api_ip)
        expected = {
            'private-address': u.valid_ip,
            'quantum_region': 'RegionOne',
            'quantum_service': 'quantum',
            'quantum_admin_url': api_endpoint,
            'quantum_internal_url': api_endpoint,
            'quantum_public_url': api_endpoint,
        }

        ret = u.validate_relation_data(unit, relation, expected)
        if ret:
            message = u.relation_error('neutron-api identity-service', ret)
            amulet.raise_status(amulet.FAIL, msg=message)

    def test_keystone_neutron_api_identity_relation(self):
        """Verify the keystone to neutron-api identity-service relation data"""
        unit = self.keystone_sentry
        relation = ['identity-service', 'neutron-api:identity-service']
        id_relation = unit.relation('identity-service',
                                    'neutron-api:identity-service')
        id_ip = id_relation['private-address']
        expected = {
            'admin_token': 'ubuntutesting',
            'auth_host': id_ip,
            'auth_port': "35357",
            'auth_protocol': 'http',
            'private-address': id_ip,
            'service_host': id_ip,
        }
        ret = u.validate_relation_data(unit, relation, expected)
        if ret:
            message = u.relation_error('neutron-api identity-service', ret)
            amulet.raise_status(amulet.FAIL, msg=message)

    def test_neutron_api_plugin_relation(self):
        """Verify neutron-api to neutron-openvswitch neutron-plugin-api"""
        unit = self.neutron_api_sentry
        relation = ['neutron-plugin-api',
                    'neutron-openvswitch:neutron-plugin-api']
        expected = {
            'private-address': u.valid_ip,
        }
        ret = u.validate_relation_data(unit, relation, expected)
        if ret:
            message = u.relation_error('neutron-api neutron-plugin-api', ret)
            amulet.raise_status(amulet.FAIL, msg=message)

    # XXX Test missing to examine the relation data neutron-openvswitch is
    #     receiving. Current;y this data cannot be interegated due to
    #     Bug#1421388

    def test_z_restart_on_config_change(self):
        """Verify that the specified services are restarted when the config
           is changed.

           Note(coreycb): The method name with the _z_ is a little odd
           but it forces the test to run last.  It just makes things
           easier because restarting services requires re-authorization.
           """
        conf = '/etc/neutron/neutron.conf'
        services = ['neutron-server']
        self.d.configure('neutron-api', {'use-syslog': 'True'})
        stime = 60
        for s in services:
            if not u.service_restarted(self.neutron_api_sentry, s, conf,
                                       pgrep_full=True, sleep_time=stime):
                self.d.configure('neutron-api', {'use-syslog': 'False'})
                msg = "service {} didn't restart after config change".format(s)
                amulet.raise_status(amulet.FAIL, msg=msg)
            stime = 0
        self.d.configure('neutron-api', {'use-syslog': 'False'})

    def test_neutron_api_novacc_relation(self):
        """Verify the neutron-api to nova-cloud-controller relation data"""
        unit = self.neutron_api_sentry
        relation = ['neutron-api', 'nova-cloud-controller:neutron-api']
        api_ip = unit.relation('identity-service',
                               'keystone:identity-service')['private-address']
        api_endpoint = "http://%s:9696" % (api_ip)
        expected = {
            'private-address': api_ip,
            'neutron-plugin': 'ovs',
            'neutron-security-groups': "no",
            'neutron-url': api_endpoint,
        }
        ret = u.validate_relation_data(unit, relation, expected)
        if ret:
            message = u.relation_error('neutron-api neutron-api', ret)
            amulet.raise_status(amulet.FAIL, msg=message)

    def test_novacc_neutron_api_relation(self):
        """Verify the nova-cloud-controller to neutron-api relation data"""
        unit = self.nova_cc_sentry
        relation = ['neutron-api', 'neutron-api:neutron-api']
        cc_ip = unit.relation('neutron-api',
                              'neutron-api:neutron-api')['private-address']
        cc_endpoint = "http://%s:8774/v2" % (cc_ip)
        expected = {
            'private-address': cc_ip,
            'nova_url': cc_endpoint,
        }
        ret = u.validate_relation_data(unit, relation, expected)
        if ret:
            message = u.relation_error('nova-cc neutron-api', ret)
            amulet.raise_status(amulet.FAIL, msg=message)

    def test_neutron_config(self):
        """Verify the data in the neutron config file."""
        unit = self.neutron_api_sentry
        cc_relation = self.nova_cc_sentry.relation('neutron-api',
                                                   'neutron-api:neutron-api')
        rabbitmq_relation = self.rabbitmq_sentry.relation('amqp',
                                                          'neutron-api:amqp')
        ks_rel = self.keystone_sentry.relation('identity-service',
                                               'neutron-api:identity-service')

        nova_auth_url = '%s://%s:%s/v2.0' % (ks_rel['auth_protocol'],
                                             ks_rel['auth_host'],
                                             ks_rel['auth_port'])
        db_relation = self.mysql_sentry.relation('shared-db',
                                                 'neutron-api:shared-db')
        db_conn = 'mysql://neutron:%s@%s/neutron' % (db_relation['password'],
                                                     db_relation['db_host'])
        conf = '/etc/neutron/neutron.conf'
        expected = {
            'DEFAULT': {
                'verbose': 'False',
                'debug': 'False',
                'bind_port': '9686',
                'nova_url': cc_relation['nova_url'],
                'nova_region_name': 'RegionOne',
                'nova_admin_username': ks_rel['service_username'],
                'nova_admin_tenant_id': ks_rel['service_tenant_id'],
                'nova_admin_password': ks_rel['service_password'],
                'nova_admin_auth_url': nova_auth_url,
            },
            'keystone_authtoken': {
                'signing_dir': '/var/cache/neutron',
                'admin_tenant_name': 'services',
                'admin_user': 'quantum',
                'admin_password': ks_rel['service_password'],
            },
            'database': {
                'connection': db_conn,
            },
        }

        if self._get_openstack_release() >= self.trusty_kilo:
            # Kilo or later
            expected.update(
                {
                    'oslo_messaging_rabbit': {
                        'rabbit_userid': 'neutron',
                        'rabbit_virtual_host': 'openstack',
                        'rabbit_password': rabbitmq_relation['password'],
                        'rabbit_host': rabbitmq_relation['hostname']
                    }
                }
            )
        else:
            # Juno or earlier
            expected['DEFAULT'].update(
                {
                    'rabbit_userid': 'neutron',
                    'rabbit_virtual_host': 'openstack',
                    'rabbit_password': rabbitmq_relation['password'],
                    'rabbit_host': rabbitmq_relation['hostname']
                }
            )
            expected['keystone_authtoken'].update(
                {
                    'service_protocol': ks_rel['service_protocol'],
                    'service_host': ks_rel['service_host'],
                    'service_port': ks_rel['service_port'],
                    'auth_host': ks_rel['auth_host'],
                    'auth_port': ks_rel['auth_port'],
                    'auth_protocol':  ks_rel['auth_protocol']
                }
            )

        for section, pairs in expected.iteritems():
            ret = u.validate_config_data(unit, conf, section, pairs)
            if ret:
                message = "neutron config error: {}".format(ret)
                amulet.raise_status(amulet.FAIL, msg=message)

    def test_ml2_config(self):
        """Verify the data in the ml2 config file. This is only available
           since icehouse."""
        unit = self.neutron_api_sentry
        conf = '/etc/neutron/plugins/ml2/ml2_conf.ini'
        neutron_api_relation = unit.relation('shared-db', 'mysql:shared-db')

        expected = {
            'ml2': {
                'type_drivers': 'gre,vxlan,vlan,flat',
                'tenant_network_types': 'gre,vxlan,vlan,flat',
            },
            'ml2_type_gre': {
                'tunnel_id_ranges': '1:1000'
            },
            'ml2_type_vxlan': {
                'vni_ranges': '1001:2000'
            },
            'ovs': {
                'enable_tunneling': 'True',
                'local_ip': neutron_api_relation['private-address']
            },
            'agent': {
                'tunnel_types': 'gre',
            },
            'securitygroup': {
                'enable_security_group': 'False',
            }
        }

        if self._get_openstack_release() >= self.trusty_kilo:
            # Kilo or later
            expected['ml2'].update(
                {
                    'mechanism_drivers': 'openvswitch,l2population'
                }
            )
        else:
            # Juno or earlier
            expected['ml2'].update(
                {
                    'mechanism_drivers': 'openvswitch,hyperv,l2population'
                }
            )

        for section, pairs in expected.iteritems():
            ret = u.validate_config_data(unit, conf, section, pairs)
            if ret:
                message = "ml2 config error: {}".format(ret)
                amulet.raise_status(amulet.FAIL, msg=message)

    def test_services(self):
        """Verify the expected services are running on the corresponding
           service units."""
        neutron_api_services = ['status neutron-server']
        neutron_services = ['status neutron-dhcp-agent',
                            'status neutron-lbaas-agent',
                            'status neutron-metadata-agent',
                            'status neutron-plugin-openvswitch-agent',
                            'status neutron-ovs-cleanup']

        if self._get_openstack_release() <= self.trusty_juno:
            neutron_services.append('status neutron-vpn-agent')

        if self._get_openstack_release() < self.trusty_kilo:
            # Juno or earlier
            neutron_services.append('status neutron-metering-agent')

        nova_cc_services = ['status nova-api-ec2',
                            'status nova-api-os-compute',
                            'status nova-objectstore',
                            'status nova-cert',
                            'status nova-scheduler',
                            'status nova-conductor']

        commands = {
            self.mysql_sentry: ['status mysql'],
            self.keystone_sentry: ['status keystone'],
            self.nova_cc_sentry: nova_cc_services,
            self.quantum_gateway_sentry: neutron_services,
            self.neutron_api_sentry: neutron_api_services,
        }

        ret = u.validate_services(commands)
        if ret:
            amulet.raise_status(amulet.FAIL, msg=ret)
