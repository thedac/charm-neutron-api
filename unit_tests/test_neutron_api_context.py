from test_utils import CharmTestCase
from mock import patch
import neutron_api_context as context

TO_PATCH = [
    'relation_get',
    'relation_ids',
    'related_units',
    'config',
]


class NeutronAPIContextsTest(CharmTestCase):

    def setUp(self):
        super(NeutronAPIContextsTest, self).setUp(context, TO_PATCH)
        self.relation_get.side_effect = self.test_relation.get
        self.config.side_effect = self.test_config.get
        self.test_config.set('neutron-plugin', 'ovs')
        self.test_config.set('neutron-security-groups', True)
        self.test_config.set('debug', True)
        self.test_config.set('verbose', True)
        self.test_config.set('neutron-external-network', 'bob')

    def tearDown(self):
        super(NeutronAPIContextsTest, self).tearDown()

    @patch.object(context.NeutronCCContext, 'network_manager')
    @patch.object(context.NeutronCCContext, 'plugin')
    def test_quantum_plugin_context_no_setting(self, plugin, nm):
        plugin.return_value = None
        napi_ctxt = context.NeutronCCContext()
        ctxt_data = {
            'debug': True,
            'external_network': 'bob',
            'verbose': True
        }
        with patch.object(napi_ctxt, '_ensure_packages'):
            self.assertEquals(ctxt_data, napi_ctxt())

    def test_quantum_plugin_context_manager(self):
        napi_ctxt = context.NeutronCCContext()
        self.assertEquals(napi_ctxt.network_manager, 'neutron')
        self.assertEquals(napi_ctxt.plugin, 'ovs')
        self.assertEquals(napi_ctxt.neutron_security_groups, True)

    def test_quantum_plugin_context_manager_pkgs(self):
        napi_ctxt = context.NeutronCCContext()
        with patch.object(napi_ctxt, '_ensure_packages') as ep:
            napi_ctxt._ensure_packages()
            ep.assert_has_calls([])
