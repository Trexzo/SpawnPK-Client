import json
import unittest
from scan_v309_network import AuditRefused, PIN
from verify_r355 import verify_text

def base():
    return {
        "schema":"R355_ORIGINAL_V309_NETWORK_BYTECODE_INVOKES_V1",
        "original_jar_sha256":PIN,
        "original_jar_bytes":17532075,
        "scope":"rs/ classes only; method-level direct invocation instructions",
        "original_jar_executed":False,"os_egress_attested":False,
        "runtime_network_destinations_verified":False,"login_verified":False,
        "same_pid_reconnect_verified":False,
        "classes_scanned":1,"network_invocations_count":1,
        "network_calling_classes_count":1,
        "indirect_invocation_or_reflection_count":0,"indirect_calling_classes_count":0,
        "known_client_b_getByName_seen":True,"known_client_b_socket_init_seen":True,
        "startup_class_network_callsite_count":0,
        "nominal_launcher_main_roots":0,
        "nominal_startup_reachable_network_calls_count":0,
        "nominal_startup_paths_truncated":False,
        "nominal_startup_network_paths":[],
        "nominal_startup_path_hop_limit":12,
        "network_calls":[{"class":"rs.Client","method":"b", "method_descriptor":"(I)V",
             "bytecode_offset":10,"opcode":"0xb8", "target_class":"java.net.InetAddress",
             "target_method":"getByName","target_descriptor":"(Ljava/lang/String;)Ljava/net/InetAddress;"}]
    }

class VerifyTests(unittest.TestCase):
    def valid(self,x):return verify_text(json.dumps(x))
    def test_valid_shape_is_explicitly_unattested(self):
        result=self.valid(base())
        self.assertEqual(result['status'],'R355_REPORT_SHAPE_CONSISTENT_UNATTESTED')
        self.assertFalse(result['runtime_admitted'])
    def test_reject_false_runtime_claims(self):
        for key in ['original_jar_executed','os_egress_attested',
                    'runtime_network_destinations_verified','login_verified','same_pid_reconnect_verified']:
            for value in (True,1,'yes'):
                x=base();x[key]=value
                with self.subTest(key=key,value=value),self.assertRaises(AuditRefused):self.valid(x)
    def test_reject_wrong_pin_and_missing_baseline(self):
        for key,value in [('original_jar_sha256','0'*64),('original_jar_bytes',False),
                          ('known_client_b_socket_init_seen',False),('network_invocations_count',True)]:
            x=base();x[key]=value
            with self.subTest(key=key),self.assertRaises(AuditRefused):self.valid(x)
    def test_reject_bad_rows_and_secrets(self):
        bads=[('target_class','https://example.com'),('bytecode_offset',False),
              ('target_method','host=secret.host.invalid'),('opcode','0xbb'),('class','third.party')]
        for key,value in bads:
            x=base();x['network_calls'][0][key]=value
            with self.subTest(key=key),self.assertRaises(AuditRefused):self.valid(x)
    def test_reject_extra_and_duplicate_keys(self):
        x=base();x['new_claim']=True
        with self.assertRaises(AuditRefused):self.valid(x)
        raw=json.dumps(base()).replace('"login_verified": false,','"login_verified": false, "login_verified": false,')
        with self.assertRaises(AuditRefused):verify_text(raw)
    def test_valid_nominal_startup_path_is_not_runtime_proof(self):
        x=base()
        x['nominal_launcher_main_roots']=1
        x['nominal_startup_reachable_network_calls_count']=1
        x['nominal_startup_network_paths']=[{
            'class':'rs.Client','method':'b','target_class':'java.net.InetAddress',
            'target_method':'getByName','nominal_hops_from_launcher_main':1,
            'path':['rs.gui.Launcher#main([Ljava/lang/String;)V','rs.Client#b(I)V']
        }]
        receipt=self.valid(x)
        self.assertFalse(receipt['runtime_admitted'])
        x['nominal_startup_network_paths'][0]['path'][1]='rs.Client#<init>(I)V'
        with self.assertRaises(AuditRefused):self.valid(x)

    def test_reject_nominal_reachability_forgery(self):
        x=base();x['nominal_startup_reachable_network_calls_count']=1
        with self.assertRaises(AuditRefused):self.valid(x)
        x=base();x['nominal_startup_path_hop_limit']=13
        with self.assertRaises(AuditRefused):self.valid(x)
        x=base();x['nominal_startup_paths_truncated']=True
        with self.assertRaises(AuditRefused):self.valid(x)

    def test_reject_incorrect_totals(self):
        for key,value in [('network_calling_classes_count',0),('startup_class_network_callsite_count',1),
                          ('network_invocations_count',2)]:
            x=base();x[key]=value
            with self.subTest(key=key),self.assertRaises(AuditRefused):self.valid(x)

if __name__=='__main__':unittest.main(verbosity=2)
