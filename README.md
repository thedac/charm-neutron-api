# Overview 

This principle charm provides the OpenStack Neutron API service which was previously provided by the nova-cloud-controller charm.

When this charm is related to the nova-cloud-controller charm the nova-cloud controller charm will shutdown its api service, de-register it from keystone and inform the compute nodes of the new neutron url.

# Usage

To deploy (partial deployment only):

    juju deploy neutron-api
    juju deploy neutron-openvswitch

    juju add-relation neutron-api mysql
    juju add-relation neutron-api rabbitmq-server
    juju add-relation neutron-api neutron-openvswitch
    juju add-relation neutron-api nova-cloud-controller

This charm also supports scale out and high availability using the hacluster charm:

    juju deploy hacluster neutron-hacluster
    juju add-unit neutron-api
    juju set neutron-api vip=<VIP FOR ACCESS>
    juju add-relation neutron-hacluster neutron-api

# Deploying from source

The minimum openstack-origin-git config required to deploy from source is:

  openstack-origin-git:
      "repositories:
         - {name: requirements,
            repository: 'git://git.openstack.org/openstack/requirements',
            branch: stable/juno}
         - {name: neutron,
            repository: 'git://git.openstack.org/openstack/neutron',
            branch: stable/juno}"

Note that there are only two 'name' values the charm knows about: 'requirements'
and 'neutron'. These repositories must correspond to these 'name' values.
Additionally, the requirements repository must be specified first and the
neutron repository must be specified last. All other repostories are installed
in the order in which they are specified.

The following is a full list of current tip repos (may not be up-to-date):

  openstack-origin-git:
      "repositories:
         - {name: requirements,
            repository: 'git://git.openstack.org/openstack/requirements',
            branch: master}
         - {name: oslo-concurrency,
            repository: 'git://git.openstack.org/openstack/oslo.concurrency',
            branch: master}
         - {name: oslo-config,
            repository: 'git://git.openstack.org/openstack/oslo.config',
            branch: master}
         - {name: oslo-context,
            repository: 'git://git.openstack.org/openstack/oslo.context.git',
            branch: master}
         - {name: oslo-db,
            repository: 'git://git.openstack.org/openstack/oslo.db',
            branch: master}
         - {name: oslo-i18n,
            repository: 'git://git.openstack.org/openstack/oslo.i18n',
            branch: master}
         - {name: oslo-messaging,
            repository: 'git://git.openstack.org/openstack/oslo.messaging.git',
            branch: master}
         - {name: oslo-middleware,
            repository': 'git://git.openstack.org/openstack/oslo.middleware.git',
            branch: master}
         - {name: oslo-rootwrap',
            repository: 'git://git.openstack.org/openstack/oslo.rootwrap.git',
            branch: master}
         - {name: oslo-serialization,
            repository: 'git://git.openstack.org/openstack/oslo.serialization',
            branch: master}
         - {name: oslo-utils,
            repository: 'git://git.openstack.org/openstack/oslo.utils',
            branch: master}
         - {name: pbr,
            repository: 'git://git.openstack.org/openstack-dev/pbr',
            branch: master}
         - {name: stevedore,
            repository: 'git://git.openstack.org/openstack/stevedore.git',
            branch: 'master'}
         - {name: python-keystoneclient,
            repository: 'git://git.openstack.org/openstack/python-keystoneclient',
            branch: master}
         - {name: python-neutronclient,
            repository: 'git://git.openstack.org/openstack/python-neutronclient.git',
            branch: master}
         - {name: python-novaclient,
            repository': 'git://git.openstack.org/openstack/python-novaclient.git',
            branch: master}
         - {name: keystonemiddleware,
            repository: 'git://git.openstack.org/openstack/keystonemiddleware',
            branch: master}
         - {name: neutron-fwaas,
            repository': 'git://git.openstack.org/openstack/neutron-fwaas.git',
            branch: master}
         - {name: neutron-lbaas,
            repository: 'git://git.openstack.org/openstack/neutron-lbaas.git',
            branch: master}
         - {name: neutron-vpnaas,
            repository: 'git://git.openstack.org/openstack/neutron-vpnaas.git',
            branch: master}
         - {name: neutron,
            repository: 'git://git.openstack.org/openstack/neutron',
            branch: master}"

# Restrictions

This charm only support deployment with OpenStack Icehouse or better.
