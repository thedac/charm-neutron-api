#!/usr/bin/python

import sys

from charmhelpers.core.hookenv import (
    Hooks,
    UnregisteredHookError,
    config,
    is_relation_made,
    log,
    ERROR,
    relation_get,
    relation_ids,
    relation_set,
    related_units,
    open_port,
    unit_get,
)

from charmhelpers.core.host import (
    restart_on_change
)

from charmhelpers.fetch import (
    apt_install, apt_update
)

from charmhelpers.contrib.openstack.utils import (
    configure_installation_source,
    openstack_upgrade_available,
)
from charmhelpers.contrib.openstack.neutron import (
    network_manager,
    neutron_plugin_attribute,                                                                                                                                                                                 
)

from neutron_api_utils import (
    determine_endpoints,
    determine_packages,
    determine_ports,
    register_configs,
    restart_map,
    NEUTRON_CONF,
    api_port,
    auth_token_config,
    keystone_ca_cert_b64,
)

from charmhelpers.contrib.hahelpers.cluster import (
    canonical_url,
)

from charmhelpers.payload.execd import execd_preinstall

hooks = Hooks()
CONFIGS = register_configs()


@hooks.hook()
def install():
    execd_preinstall()
    configure_installation_source(config('openstack-origin'))
    apt_update()
    apt_install(determine_packages(), fatal=True)
    [open_port(port) for port in determine_ports()]


@hooks.hook('config-changed')
@restart_on_change(restart_map(), stopstart=True)
def config_changed():
    global CONFIGS
    CONFIGS.write_all()


@hooks.hook('amqp-relation-joined')
def amqp_joined(relation_id=None):
    relation_set(relation_id=relation_id,
                 username=config('rabbit-user'), vhost=config('rabbit-vhost'))


@hooks.hook('amqp-relation-changed')
@hooks.hook('amqp-relation-departed')
@restart_on_change(restart_map())
def amqp_changed():
    if 'amqp' not in CONFIGS.complete_contexts():
        log('amqp relation incomplete. Peer not ready?')
        return
    CONFIGS.write(NEUTRON_CONF)


@hooks.hook('shared-db-relation-joined')
def db_joined():
    if is_relation_made('pgsql-nova-db') or \
            is_relation_made('pgsql-neutron-db'):
        # error, postgresql is used
        e = ('Attempting to associate a mysql database when there is already '
             'associated a postgresql one')
        log(e, level=ERROR)
        raise Exception(e)

    relation_set(neutron_database=config('database'),
                 neutron_username=config('database-user'),
                 neutron_hostname=unit_get('private-address'))


@hooks.hook('pgsql-neutron-db-relation-joined')
def pgsql_neutron_db_joined():
    if is_relation_made('shared-db'):
        # raise error
        e = ('Attempting to associate a postgresql database'
             ' when there is already associated a mysql one')
        log(e, level=ERROR)
        raise Exception(e)

    relation_set(database=config('database'))


@hooks.hook('shared-db-relation-changed')
@restart_on_change(restart_map())
def db_changed():
    if 'shared-db' not in CONFIGS.complete_contexts():
        log('shared-db relation incomplete. Peer not ready?')
        return
    CONFIGS.write_all()

@hooks.hook('pgsql-neutron-db-relation-changed')
@restart_on_change(restart_map())
def postgresql_neutron_db_changed():
    if network_manager() in ['neutron', 'quantum']:
        plugin = config('neutron-plugin')
        # DB config might have been moved to main neutron.conf in H?
        CONFIGS.write(neutron_plugin_attribute(plugin, 'config'))

def _auth_config():
    '''Grab all KS auth token config from api-paste.ini, or return empty {}'''
    ks_auth_host = auth_token_config('auth_host')
    if not ks_auth_host:
        # if there is no auth_host set, identity-service changed hooks
        # have not fired, yet.
        return {}
    cfg = {
        'auth_host': ks_auth_host,
        'auth_port': auth_token_config('auth_port'),
        'auth_protocol': auth_token_config('auth_protocol'),
        'service_protocol': auth_token_config('service_protocol'),
        'service_port': auth_token_config('service_port'),
        'service_username': auth_token_config('admin_user'),
        'service_password': auth_token_config('admin_password'),
        'service_tenant_name': auth_token_config('admin_tenant_name'),
        'auth_uri': auth_token_config('auth_uri'),
        # quantum-gateway interface deviates a bit.
        'keystone_host': ks_auth_host,
        'service_tenant': auth_token_config('admin_tenant_name'),
    }
    return cfg


@hooks.hook('amqp-relation-broken',
            'identity-service-relation-broken',
            'shared-db-relation-broken',
            'pgsql-neutron-db-relation-broken')
def relation_broken():
    CONFIGS.write_all()

@hooks.hook('upgrade-charm')
def upgrade_charm():
    for r_id in relation_ids('amqp'):
        amqp_joined(relation_id=r_id)
    for r_id in relation_ids('identity-service'):
        identity_joined(rid=r_id)

@hooks.hook('identity-service-relation-joined')
def identity_joined(rid=None):
    base_url = canonical_url(CONFIGS)
    relation_set(relation_id=rid, **determine_endpoints(base_url))

@hooks.hook('identity-service-relation-changed')
@restart_on_change(restart_map())
def identity_changed():
    if 'identity-service' not in CONFIGS.complete_contexts():
        log('identity-service relation incomplete. Peer not ready?')
        return
    CONFIGS.write(NEUTRON_CONF)
    for r_id in relation_ids('neutron-api'):
        neutron_api_relation_joined(rid=r_id)
 
def _get_keystone_info():
    keystone_info = {}
    for lrid in relation_ids('identity-service'):
        for unit in related_units(lrid):
            rdata = relation_get(rid=lrid, unit=unit)
            keystone_info['service_protocol'] = rdata.get('service_protocol') 
            keystone_info['service_host'] = rdata.get('service_host') 
            keystone_info['service_port'] = rdata.get('service_port') 
            keystone_info['service_tenant'] = rdata.get('service_tenant') 
            keystone_info['service_username'] = rdata.get('service_username') 
            keystone_info['service_password'] = rdata.get('service_password') 
            keystone_info['auth_url'] = "%s://%s:%s/v2.0" % (keystone_info['service_protocol'],
                                                             keystone_info['service_host'],
                                                             keystone_info['service_port'])
    return keystone_info

@hooks.hook('neutron-api-relation-joined')
def neutron_api_relation_joined(rid=None):
    manager = network_manager()
    base_url = canonical_url(CONFIGS)
    neutron_url = '%s:%s' % (base_url, api_port('neutron-server'))
    relation_data = {
        'network_manager': manager,
        'default_floating_pool': config('neutron-external-network'),
        'external_network': config('neutron-external-network'),
        manager + '_plugin': config('neutron-plugin'),
        manager + '_url': neutron_url,
        manager + '_security_groups': config('neutron-security-groups')
    }
    keystone_info = _get_keystone_info()
    if is_relation_made('identity-service') and keystone_info:
        relation_data.update({
            manager + '_admin_tenant_name': keystone_info['service_tenant'],
            manager + '_admin_username': keystone_info['service_username'],
            manager + '_admin_password': keystone_info['service_password'],
            manager + '_admin_auth_url': keystone_info['auth_url'],
        })
    relation_set(relation_id=rid, **relation_data)
    # Nova-cc may have grabbed the quantum endpoint so kick identity-service relation to
    # register that its here
    for r_id in relation_ids('identity-service'):
        identity_joined(rid=r_id)

@hooks.hook('neutron-api-relation-changed')
@restart_on_change(restart_map())
def neutron_api_relation_changed():
    CONFIGS.write(NEUTRON_CONF)

def main():
    try:
        hooks.execute(sys.argv)
    except UnregisteredHookError as e:
        log('Unknown hook {} - skipping.'.format(e))


if __name__ == '__main__':
    main()
