"""R82: strict StringConcatFactory -> BufferedWriter Java source forms."""
import copy
import unittest
from spk_recovery.properties_save_writer_source import (
    _concat, _writer, extract_writer_lines,
)

def fixture():
    owner="p/Settings"
    field={"offset":1,"length":3,"opcode":"0xb2","owner":owner,
           "name":"flag","descriptor":"Z"}
    rows=[
        {"offset":0,"length":1,"opcode":"0x2b"},
        field,
        {"offset":4,"length":5,"opcode":"0xba","name":"makeConcatWithConstants",
         "descriptor":"(Z)Ljava/lang/String;",
         "bootstrap_method_attr_index":0,"invokedynamic_reserved":0},
        {"offset":9,"length":3,"opcode":"0xb6","owner":"java/io/BufferedWriter",
         "name":"write","descriptor":"(Ljava/lang/String;)V"},
        {"offset":12,"length":1,"opcode":"0x2b"},
        {"offset":13,"length":3,"opcode":"0xb6","owner":"java/io/BufferedWriter",
         "name":"newLine","descriptor":"()V"},
    ]
    profile={"internal_name":owner,"fields":[
        {"name":"flag","descriptor":"Z","access":0x0009,
         "signature":None,"constant_value":None}],
        "bootstrap_methods":[{"bootstrap_method":{
            "owner":"java/lang/invoke/StringConcatFactory",
            "name":"makeConcatWithConstants","reference_kind":6},
            "arguments":[{"kind":"string","value":"flag=\\u0001".replace("\\u0001","\x01")}]}]}
    return profile,{"instructions":rows,"code_length":16}

class ExactWriterSourceTests(unittest.TestCase):
    def test_one_verified_original_Boolean_write_then_newline(self):
        profile,method=fixture()
        fragments=extract_writer_lines(profile,method)
        self.assertEqual(len(fragments),1)
        self.assertIn('originalLocalSlot1.write("flag=" + flag);',
                      fragments[0]["private_java_source_fragment"])
        self.assertIn("originalLocalSlot1.newLine();",
                      fragments[0]["private_java_source_fragment"])

    def test_changed_bootstrap_recipe_and_member_fail_closed(self):
        original,method=fixture()
        changed=copy.deepcopy(original)
        changed["bootstrap_methods"][0]["arguments"][0]["value"]="unexpected\x02"
        self.assertEqual(extract_writer_lines(changed,method),[])
        bad=copy.deepcopy(method)
        bad["instructions"][3]["name"]="readLine"
        self.assertEqual(extract_writer_lines(original,bad),[])
        bad=copy.deepcopy(original)
        bad["fields"][0]["access"]=0
        self.assertEqual(extract_writer_lines(bad,method),[])

    def test_unaccounted_incoming_branch_and_signature_fail_closed(self):
        profile,method=fixture()
        wrong=copy.deepcopy(method)
        wrong["instructions"][2]["descriptor"]="(I)Ljava/lang/String;"
        self.assertEqual(extract_writer_lines(profile,wrong),[])
        wrong=copy.deepcopy(method)
        wrong["instructions"].append({
            "offset":16,"length":3,"opcode":"0xa7","branch_target_offset":4
        })
        self.assertEqual(extract_writer_lines(profile,wrong),[])

if __name__=="__main__":
    unittest.main()
