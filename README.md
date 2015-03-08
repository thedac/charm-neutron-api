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

The minimal openstack-origin-git config required to deploy from source is:

  openstack-origin-git:
      "{'neutron':
           {'repository': 'git://git.openstack.org/openstack/neutron.git',
            'branch': 'stable/icehouse'}}"

If you specify a 'requirements' repository, it will be used to update the
requirements.txt files of all other git repos that it applies to, before
they are installed:

  openstack-origin-git:
      "{'requirements':
           {'repository': 'git://git.openstack.org/openstack/requirements.git',
            'branch': 'master'},
        'neutron':
           {'repository': 'git://git.openstack.org/openstack/neutron.git',
            'branch': 'master'}}"

Note that there are only two key values the charm knows about for the outermost
dictionary: 'neutron' and 'requirements'. These repositories must correspond to
these keys. If the requirements repository is specified, it will be installed
first. The neutron repository is always installed last.  All other repostories
will be installed in between.

NOTE(coreycb): The following is temporary to keep track of the full list of
current tip repos (may not be up-to-date).

  openstack-origin-git:
      "{'requirements':
           {'repository': 'git://git.openstack.org/openstack/requirements.git',
            'branch': 'master'},
        'neutron-fwaas':
           {'repository': 'git://git.openstack.org/openstack/neutron-fwaas.git',
            'branch': 'master'},
        'neutron-lbaas':
           {'repository: 'git://git.openstack.org/openstack/neutron-lbaas.git',
            'branch': 'master'},
        'neutron-vpnaas':
           {'repository: 'git://git.openstack.org/openstack/neutron-vpnaas.git',
            'branch': 'master'},
        'keystonemiddleware:
           {'repository': 'git://git.openstack.org/openstack/keystonemiddleware.git',
            'branch: 'master'},
        'oslo-concurrency':
           {'repository': 'git://git.openstack.org/openstack/oslo.concurrency.git',
            'branch: 'master'},
        'oslo-config':
           {'repository': 'git://git.openstack.org/openstack/oslo.config.git',
            'branch: 'master'},
        'oslo-context':
           {'repository': 'git://git.openstack.org/openstack/oslo.context.git',
            'branch: 'master'},
        'oslo-db':
           {'repository': 'git://git.openstack.org/openstack/oslo.db.git',
            'branch: 'master'},
        'oslo-i18n':
           {'repository': 'git://git.openstack.org/openstack/oslo.i18n.git',
            'branch: 'master'},
        'oslo-messaging':
           {'repository': 'git://git.openstack.org/openstack/oslo.messaging.git',
            'branch: 'master'},
        'oslo-middleware:
           {'repository': 'git://git.openstack.org/openstack/oslo.middleware.git',
            'branch': 'master'},
        'oslo-rootwrap':
           {'repository': 'git://git.openstack.org/openstack/oslo.rootwrap.git',
            'branch: 'master'},
        'oslo-serialization':
           {'repository': 'git://git.openstack.org/openstack/oslo.serialization.git',
            'branch: 'master'},
        'oslo-utils':
           {'repository': 'git://git.openstack.org/openstack/oslo.utils.git',
            'branch: 'master'},
        'pbr':
           {'repository': 'git://git.openstack.org/openstack-dev/pbr.git',
            'branch: 'master'},
        'python-keystoneclient':
           {'repository': 'git://git.openstack.org/openstack/python-keystoneclient.git',
            'branch: 'master'},
        'python-neutronclient':
           {'repository': 'git://git.openstack.org/openstack/python-neutronclient.git',
            'branch: 'master'},
        'python-novaclient':
           {'repository': 'git://git.openstack.org/openstack/python-novaclient.git',
            'branch: 'master'},
        'stevedore':
           {'repository': 'git://git.openstack.org/openstack/stevedore.git',
            'branch: 'master'},
        'neutron':
           {'repository': 'git://git.openstack.org/openstack/neutron.git',
            'branch': 'master'}}"

# Restrictions

This charm only support deployment with OpenStack Icehouse or better.
