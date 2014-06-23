Overview                                                                                                                                                                                                      
--------

This principle charm provides the Neutron API service which was previously
provided by the nova-cloud-controller charm. When this charm is joined with
the nova-cc charm the nova-cc charm will shutdown its api service, deregister
it from neutron and inform the compute nodes of the new neutron url. This
charm expects the following relations:

1) neutron-plugin-api relation with subordinate neutron plugin charms
   (such as neutron-openvswitch)
2) neutron-api relation with nova-cloud-controller
3) Database backend
4) amqp relation with message broker. If a single message broker is being used for 
   the openstack deployemnt then it can relat to that. If a seperate neutron 
   message broker is being used it should relate to that.
5) identity-service relation
6) ha relation with ha subordinate
