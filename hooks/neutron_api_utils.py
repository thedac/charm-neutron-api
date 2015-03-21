from collections import OrderedDict
from copy import deepcopy
import os
import shutil
import yaml
from base64 import b64encode
from charmhelpers.contrib.openstack import context, templating
from charmhelpers.contrib.openstack.neutron import (
    neutron_plugin_attribute,
)

from charmhelpers.contrib.openstack.utils import (
    os_release,
    get_os_codename_install_source,
    git_install_requested,
    git_clone_and_install,
    git_src_dir,
    configure_installation_source,
)

from charmhelpers.core.hookenv import (
    config,
    log,
)

from charmhelpers.fetch import (
    apt_update,
    apt_install,
    apt_upgrade,
    add_source
)

from charmhelpers.core.host import (
    adduser,
    add_group,
    add_user_to_group,
    mkdir,
    lsb_release,
    write_file,
)

import neutron_api_context

TEMPLATES = 'templates/'

CLUSTER_RES = 'grp_neutron_vips'

# removed from original: charm-helper-sh
BASE_PACKAGES = [
    'apache2',
    'haproxy',
    'python-keystoneclient',
    'python-mysqldb',
    'python-psycopg2',
    'python-six',
    'uuid',
]

KILO_PACKAGES = [
    'python-neutron-lbaas',
    'python-neutron-fwaas',
    'python-neutron-vpnaas',
]

BASE_GIT_PACKAGES = [
    'libxml2-dev',
    'libxslt1-dev',
    'python-dev',
    'python-pip',
    'python-setuptools',
    'zlib1g-dev',
]

# ubuntu packages that should not be installed when deploying from git
GIT_PACKAGE_BLACKLIST = [
    'neutron-server',
    'python-keystoneclient',
]

GIT_PACKAGE_BLACKLIST_KILO = [
    'python-neutron-lbaas',
    'python-neutron-fwaas',
    'python-neutron-vpnaas',
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
                         user=config('database-user'),
                         database=config('database'),
                         ssl_dir=NEUTRON_CONF_DIR),
                     context.PostgresqlDBContext(database=config('database')),
                     neutron_api_context.IdentityServiceContext(
                         service='neutron',
                         service_user='neutron'),
                     neutron_api_context.NeutronCCContext(),
                     context.SyslogContext(),
                     context.BindHostContext(),
                     context.WorkerConfigContext()],
    }),
    (NEUTRON_DEFAULT, {
        'services': ['neutron-server'],
        'contexts': [neutron_api_context.NeutronCCContext()],
    }),
    (APACHE_CONF, {
        'contexts': [neutron_api_context.ApacheSSLContext()],
        'services': ['apache2'],
    }),
    (APACHE_24_CONF, {
        'contexts': [neutron_api_context.ApacheSSLContext()],
        'services': ['apache2'],
    }),
    (HAPROXY_CONF, {
        'contexts': [context.HAProxyContext(singlenode_mode=True),
                     neutron_api_context.HAProxyContext()],
        'services': ['haproxy'],
    }),
])


def api_port(service):
    return API_PORTS[service]


def determine_packages(source=None):
    # currently all packages match service names
    packages = [] + BASE_PACKAGES

    for v in resource_map().values():
        packages.extend(v['services'])
        pkgs = neutron_plugin_attribute(config('neutron-plugin'),
                                        'server_packages',
                                        'neutron')
        packages.extend(pkgs)

    if get_os_codename_install_source(source) >= 'kilo':
        packages.extend(KILO_PACKAGES)

    if git_install_requested():
        packages.extend(BASE_GIT_PACKAGES)
        # don't include packages that will be installed from git
        for p in GIT_PACKAGE_BLACKLIST:
            packages.remove(p)
        if get_os_codename_install_source(source) >= 'kilo':
            for p in GIT_PACKAGE_BLACKLIST_KILO:
                packages.remove(p)

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

    if os.path.exists('/etc/apache2/conf-available'):
        resource_map.pop(APACHE_CONF)
    else:
        resource_map.pop(APACHE_24_CONF)

    # add neutron plugin requirements. nova-c-c only needs the neutron-server
    # associated with configs, not the plugin agent.
    plugin = config('neutron-plugin')
    conf = neutron_plugin_attribute(plugin, 'config', 'neutron')
    ctxts = (neutron_plugin_attribute(plugin, 'contexts', 'neutron')
             or [])
    services = neutron_plugin_attribute(plugin, 'server_services',
                                        'neutron')
    resource_map[conf] = {}
    resource_map[conf]['services'] = services
    resource_map[conf]['contexts'] = ctxts
    resource_map[conf]['contexts'].append(
        neutron_api_context.NeutronCCContext())

    # update for postgres
    resource_map[conf]['contexts'].append(
        context.PostgresqlDBContext(database=config('database')))

    return resource_map


def register_configs(release=None):
    release = release or os_release('neutron-server')
    configs = templating.OSConfigRenderer(templates_dir=TEMPLATES,
                                          openstack_release=release)
    for cfg, rscs in resource_map().iteritems():
        configs.register(cfg, rscs['contexts'])
    return configs


def restart_map():
    return OrderedDict([(cfg, v['services'])
                        for cfg, v in resource_map().iteritems()
                        if v['services']])


def services():
    ''' Returns a list of services associate with this charm '''
    _services = []
    for v in restart_map().values():
        _services = _services + v
    return list(set(_services))


def keystone_ca_cert_b64():
    '''Returns the local Keystone-provided CA cert if it exists, or None.'''
    if not os.path.isfile(CA_CERT_PATH):
        return None
    with open(CA_CERT_PATH) as _in:
        return b64encode(_in.read())


def do_openstack_upgrade(configs):
    """
    Perform an upgrade.  Takes care of upgrading packages, rewriting
    configs, database migrations and potentially any other post-upgrade
    actions.

    :param configs: The charms main OSConfigRenderer object.
    """
    new_src = config('openstack-origin')
    new_os_rel = get_os_codename_install_source(new_src)

    log('Performing OpenStack upgrade to %s.' % (new_os_rel))

    configure_installation_source(new_src)
    dpkg_opts = [
        '--option', 'Dpkg::Options::=--force-confnew',
        '--option', 'Dpkg::Options::=--force-confdef',
    ]
    apt_update(fatal=True)
    apt_upgrade(options=dpkg_opts, fatal=True, dist=True)
    pkgs = determine_packages(new_os_rel)
    # Sort packages just to make unit tests easier
    pkgs.sort()
    apt_install(packages=pkgs,
                options=dpkg_opts,
                fatal=True)

    # set CONFIGS to load templates from new release
    configs.set_release(openstack_release=new_os_rel)


def setup_ipv6():
    ubuntu_rel = lsb_release()['DISTRIB_CODENAME'].lower()
    if ubuntu_rel < "trusty":
        raise Exception("IPv6 is not supported in the charms for Ubuntu "
                        "versions less than Trusty 14.04")

    # NOTE(xianghui): Need to install haproxy(1.5.3) from trusty-backports
    # to support ipv6 address, so check is required to make sure not
    # breaking other versions, IPv6 only support for >= Trusty
    if ubuntu_rel == 'trusty':
        add_source('deb http://archive.ubuntu.com/ubuntu trusty-backports'
                   ' main')
        apt_update()
        apt_install('haproxy/trusty-backports', fatal=True)


def git_install(projects_yaml):
    """Perform setup, and install git repos specified in yaml parameter."""
    if git_install_requested():
        git_pre_install()
        git_clone_and_install(projects_yaml, core_project='neutron')
        git_post_install(projects_yaml)


def git_pre_install():
    """Perform pre-install setup."""
    dirs = [
        '/etc/neutron',
        '/etc/neutron/rootwrap.d',
        '/etc/neutron/plugins',
        '/var/lib/neutron',
        '/var/lib/neutron/lock',
        '/var/log/neutron',
    ]

    logs = [
        '/var/log/neutron/server.log',
    ]

    adduser('neutron', shell='/bin/bash', system_user=True)
    add_group('neutron', system_group=True)
    add_user_to_group('neutron', 'neutron')

    for d in dirs:
        mkdir(d, owner='neutron', group='neutron', perms=0700, force=False)

    for l in logs:
        write_file(l, '', owner='neutron', group='neutron', perms=0600)


def git_post_install(projects_yaml):
    """Perform post-install setup."""
    src_etc = os.path.join(git_src_dir(projects_yaml, 'neutron'), 'etc')
    configs = {
        'api-paste': {
            'src': os.path.join(src_etc, 'api-paste.ini'),
            'dest': '/etc/neutron/api-paste.ini',
        },
        'debug-filters': {
            'src': os.path.join(src_etc, 'neutron/rootwrap.d/debug.filters'),
            'dest': '/etc/neutron/rootwrap.d/debug.filters',
        },
        'policy': {
            'src': os.path.join(src_etc, 'policy.json'),
            'dest': '/etc/neutron/policy.json',
        },
        'rootwrap': {
            'src': os.path.join(src_etc, 'rootwrap.conf'),
            'dest': '/etc/neutron/rootwrap.conf',
        },
    }

    for conf, files in configs.iteritems():
        shutil.copyfile(files['src'], files['dest'])

    render('neutron-server.default', '/etc/default/neutron-server', {}, perms=0o440)
    render('neutron_sudoers', '/etc/sudoers.d/neutron_sudoers', {}, perms=0o440)

    neutron_api_context = {
        'service_description': 'Neutron API server',
        'charm_name': 'neutron-api',
        'process_name': 'neutron-server',
    }

    # NOTE(coreycb): Needs systemd support
    render('upstart/neutron-server.upstart', '/etc/init/neutron.conf',
           neutron_api_context, perms=0o644)

    service_start('neutron-server')
