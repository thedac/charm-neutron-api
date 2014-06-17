from charmhelpers.core.hookenv import (
    config,
    relation_ids,
    related_units,
    relation_get,
)
from charmhelpers.contrib.openstack import context

class IdentityServiceContext(context.IdentityServiceContext):

    def __call__(self):
        ctxt = super(IdentityServiceContext, self).__call__()
        if not ctxt:
            return
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
        return config('neutron-security-groups')


    def __call__(self):
        ctxt = super(NeutronCCContext, self).__call__()
        ctxt['external_network'] = config('neutron-external-network')
        for rid in relation_ids('neutron-api'):
            for unit in related_units(rid):
                ctxt['nova_url'] = relation_get(attribute='nova_url', rid=rid, unit=unit)
                if ctxt['nova_url']:
                    return ctxt
        return ctxt


