from charmhelpers.core.hookenv import (
    config,
    relation_ids,
    related_units,
    relation_get,
)
from charmhelpers.contrib.openstack import context

class NeutronPostgresqlDBContext(context.PostgresqlDBContext):
    interfaces = ['pgsql-neutron-db']

    def __init__(self):
        super(NeutronPostgresqlDBContext,
              self).__init__(config('neutron-database'))

class IdentityServiceContext(context.IdentityServiceContext):

    def __call__(self):
        ctxt = super(IdentityServiceContext, self).__call__()
        if not ctxt:
            return

        # the ec2 api needs to know the location of the keystone ec2
        # tokens endpoint, set in nova.conf
        ec2_tokens = '%s://%s:%s/v2.0/ec2tokens' % (
            ctxt['service_protocol'] or 'http',
            ctxt['service_host'],
            ctxt['service_port']
        )
        ctxt['keystone_ec2_url'] = ec2_tokens
        ctxt['region'] = config('region')
        return ctxt

class NeutronCCContext(context.NeutronContext):
    interfaces = []

    @property
    def network_manager(self):
        return 'neutron'   

    @property
    def plugin(self):
        return config('neutron-plugin')


    @property
    def neutron_security_groups(self):
        sec_groups = config('neutron-security-groups')
        return sec_groups.lower() == 'yes'


    def __call__(self):
        ctxt = super(NeutronCCContext, self).__call__()
        ctxt['external_network'] = config('neutron-external-network')
        for rid in relation_ids('neutron-api'):
            for unit in related_units(rid):
                ctxt['nova_url'] = relation_get(attribute='nova_url', rid=rid, unit=unit)
        return ctxt


