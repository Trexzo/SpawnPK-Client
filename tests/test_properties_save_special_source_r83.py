"""R83 original five exceptional save-write site proof boundaries."""
import copy
import unittest

from spk_recovery.properties_save_special_source import (
    SaveWriterSourceError, PATTERNS, original_region, recipe,
)


class SpecialSaveSourceTests(unittest.TestCase):
    def test_original_array_window_and_mutated_opcode_veto(self):
        original = PATTERNS["array"]
        self.assertEqual(len(original), 23)
        rows = [{"offset":335+i,"length":1,"opcode":opcode}
                for i,opcode in enumerate(original)]
        rows += [{"offset":380,"length":1,"opcode":"0x2b"}]
        # Synthetic offsets must reflect 45 original JVM bytes, not 23.
        position = 335
        for row, opcode in zip(rows[:-1],original):
            row["offset"] = position
            position += (5 if opcode == "0xba" else
                         3 if opcode in ("0xb2","0xb6","0xa2","0x9f",
                                         "0xa7","0x84") else 1)
        self.assertEqual(position,380)
        self.assertEqual(len(original_region(rows,335,380,"array")),23)
        rows[6]["opcode"]="0x00"
        with self.assertRaisesRegex(SaveWriterSourceError,"PATTERN_OR_END_DRIFT"):
            original_region(rows,335,380,"array")

    def test_filter_windows_and_mutation(self):
        ops=PATTERNS["filter"]
        offsets=(528,531,534,539,542,543,545,548,549)
        rows=[{"offset":offset,"length":1,"opcode":op}
              for offset,op in zip(offsets,ops)]
        rows.append({"offset":552,"length":1,"opcode":"0xb2"})
        self.assertEqual(len(original_region(rows,528,552,"filter")),9)
        rows[2]["opcode"]="0xb6"
        with self.assertRaisesRegex(SaveWriterSourceError,"PATTERN_OR_END_DRIFT"):
            original_region(rows,528,552,"filter")

    def test_bootstrap_recipe_requires_two_dynamic_slots(self):
        profile={"bootstrap_methods":[{
            "bootstrap_method":{
                "owner":"java/lang/invoke/StringConcatFactory",
                "name":"makeConcatWithConstants","reference_kind":6},
            "arguments":[{"kind":"string","value":"key_\x01=\x01"}],
        }]}
        row={"opcode":"0xba","name":"makeConcatWithConstants",
             "descriptor":"(II)Ljava/lang/String;",
             "invokedynamic_reserved":0,"bootstrap_method_attr_index":0}
        self.assertEqual(recipe(profile,row,"II",2),["key_","=",""])
        wrong=copy.deepcopy(profile)
        wrong["bootstrap_methods"][0]["arguments"][0]["value"]="wrong_\x01"
        with self.assertRaisesRegex(SaveWriterSourceError,"RECIPE_UNSUPPORTED"):
            recipe(wrong,row,"II",2)
        wrong=copy.deepcopy(profile)
        wrong["bootstrap_methods"][0]["bootstrap_method"]["name"]="bad"
        with self.assertRaisesRegex(SaveWriterSourceError,"NOT_STRING_CONCAT"):
            recipe(wrong,row,"II",2)


if __name__=="__main__":
    unittest.main()
