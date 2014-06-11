from collections import OrderedDict
from copy import deepcopy
import ConfigParser
import os
from base64 import b64encode
from charmhelpers.contrib.openstack import context, templating
from charmhelpers.contrib.openstack.neutron import (
    network_manager, neutron_plugin_attribute)

from charmhelpers.contrib.openstack.utils import (
    os_release,
)

from charmhelpers.core.hookenv import (
    config,
)

import neutron_api_context

TEMPLATES = 'templates/'

CLUSTER_RES = 'res_nova_vip'

# removed from original: charm-helper-sh
BASE_PACKAGES = [
    'python-keystoneclient',
    'python-mysqldb',
    'python-psycopg2',
    'uuid',
]

BASE_SERVICES = [
    'neutron-server'
]
API_PORTS = {
    'neutron-server': 9696,
}

NEUTRON_CONF_DIR = "/etc/neutron"

NEUTRON_CONF = '%s/neutron.conf' % NEUTRON_CONF_DIR
HAPROXY_CONF = '/etc/haproxy/haproxy.cfg'
APACHE_CONF = '/etc/apache2/sites-available/openstack_https_frontend'
APACHE_24_CONF = '/etc/apache2/sites-available/openstack_https_frontend.conf'
NEUTRON_DEFAULT = '/etc/default/neutron-server'
CA_CERT_PATH = '/usr/local/share/ca-certificates/keystone_juju_ca_cert.crt'

BASE_RESOURCE_MAP = OrderedDict([
    (NEUTRON_CONF, {
        'services': ['neutron-server'],
        'contexts': [context.AMQPContext(ssl_dir=NEUTRON_CONF_DIR),
                     context.SharedDBContext(
                         user=config('neutron-database-user'),
                         database=config('neutron-database'),
                         relation_prefix='neutron',
                         ssl_dir=NEUTRON_CONF_DIR),
                     neutron_api_context.NeutronPostgresqlDBContext(),
                     neutron_api_context.IdentityServiceContext(),
                     neutron_api_context.NeutronCCContext(),
                     context.SyslogContext()],
    }),
    (NEUTRON_DEFAULT, {
        'services': ['neutron-server'],
        'contexts': [neutron_api_context.NeutronCCContext()],
    }),
])
def api_port(service):
    return API_PORTS[service]

def determine_endpoints(url):
    '''Generates a dictionary containing all relevant endpoints to be
    passed to keystone as relation settings.'''
    region = config('region')

    neutron_url = '%s:%s' % (url, api_port('neutron-server'))

    endpoints = ({
        'quantum_service': 'quantum',
        'quantum_region': region,
        'quantum_public_url': neutron_url,
        'quantum_admin_url': neutron_url,
        'quantum_internal_url': neutron_url,
    })


    return endpoints


def determine_packages():
    # currently all packages match service names
    packages = [] + BASE_PACKAGES
    for v in resource_map().values():
        packages.extend(v['services'])
        pkgs = neutron_plugin_attribute(config('neutron-plugin'), 'server_packages',
                                        network_manager())
        packages.extend(pkgs)
    return list(set(packages))

def determine_ports():
    '''Assemble a list of API ports for services we are managing'''
    ports = []
    for services in restart_map().values():
        for service in services:
            try:
                ports.append(API_PORTS[service])
            except KeyError:
                pass
    return list(set(ports))


def resource_map():
    '''
    Dynamically generate a map of resources that will be managed for a single
    hook execution.
    '''
    resource_map = deepcopy(BASE_RESOURCE_MAP)

    net_manager = network_manager()

    # add neutron plugin requirements. nova-c-c only needs the neutron-server
    # associated with configs, not the plugin agent.
    plugin = config('neutron-plugin')
    conf = neutron_plugin_attribute(plugin, 'config', net_manager)
    ctxts = (neutron_plugin_attribute(plugin, 'contexts', net_manager)
             or [])
    services = neutron_plugin_attribute(plugin, 'server_services',
                                        net_manager)
    resource_map[conf] = {}
    resource_map[conf]['services'] = services
    resource_map[conf]['contexts'] = ctxts
    resource_map[conf]['contexts'].append(
        neutron_api_context.NeutronCCContext())

    # update for postgres
    resource_map[conf]['contexts'].append(
        neutron_api_context.NeutronPostgresqlDBContext())

    return resource_map


def register_configs(release=None):
    release = release or os_release('nova-common')
    configs = templating.OSConfigRenderer(templates_dir=TEMPLATES,
                                          openstack_release=release)
    for cfg, rscs in resource_map().iteritems():
        configs.register(cfg, rscs['contexts'])
    return configs


def restart_map():
    return OrderedDict([(cfg, v['services'])
                        for cfg, v in resource_map().iteritems()
                        if v['services']])

def auth_token_config(setting):                                                                                                                                                                               
    """
    Returns currently configured value for setting in api-paste.ini's
    authtoken section, or None.
    """
    config = ConfigParser.RawConfigParser()
    config.read('/etc/neutron/api-paste.ini')
    try:
        value = config.get('filter:authtoken', setting)
    except:
        return None
    if value.startswith('%'):
        return None
    return value

def keystone_ca_cert_b64():                                                                                                                                                                                   
    '''Returns the local Keystone-provided CA cert if it exists, or None.'''
    if not os.path.isfile(CA_CERT_PATH):
        return None
    with open(CA_CERT_PATH) as _in:
        return b64encode(_in.read())
