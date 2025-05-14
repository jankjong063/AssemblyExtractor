import re
import networkx as nx
import os
import sys
import yaml
import json
import hashlib
import csv
import py7zr
from AssemblyController import AssemblyController

INPUT_ASSEMBLY_DIR = "./input/assemblies/"
OUTPUT_FEATURE_DIR = "./output/features/"

class ConfigManager:
    def __init__(self, config_path):
        """
        Initialize the ConfigManager with the path to the YAML configuration file.
        """
        self.config_path = config_path

    def load_config(self):
        """
        Load and return the YAML configuration file as a dictionary.
        """
        with open(self.config_path, 'r') as file:
            config = yaml.safe_load(file)
        return config

    def update_config(self, key, value):
        """
        Update the YAML configuration file with a new key-value pair.
        """
        # Load the existing configuration
        with open(self.config_path, "r") as yaml_file:
            config = yaml.safe_load(yaml_file)

        # Update the configuration
        config[key] = value

        # Save the updated configuration back to the file
        with open(self.config_path, "w") as yaml_file:
            yaml.safe_dump(config, yaml_file)

def read_asm_from_7z_in_memory(archive_path, target_filename="example.asm"):
    with py7zr.SevenZipFile(archive_path, mode='r') as archive:
        all_files = archive.readall()  # returns a dict: { 'filename': file-like object }

        if target_filename in all_files:
            file_obj = all_files[target_filename]
            content = file_obj.read().decode('utf-8')  # Assuming .asm is UTF-8 encoded text
            return content
        else:
            raise FileNotFoundError(f"{target_filename} not found in {archive_path}")

def main():
    # Load configuration
    config_path = "config.yaml"
    config_manager = ConfigManager(config_path)
    config = config_manager.load_config()

    report_type = config.get("asm_analysis_report_type", 'simple')  # full, simple
    report_enable = config.get("asm_analysis_report_enable", 'enable')  # enable, disable
    selected_sections = config.get("select_sections", [])
    branch_operations = set(config.get("branch_ops", [
        'b', 'bl', 'blcc', 'blcs', 'ble.n', 'ble.w',
        'bleq', 'blge', 'blls', 'bllt', 'blmi', 'blne',
        'bls.n', 'bls.w', 'blt.n', 'blt.w', 'blvs', 'blx'
    ]))
    ignored_keys = set(config.get("ignore_keys", []))

    input_asm_file = os.path.join(INPUT_ASSEMBLY_DIR, "example.7z")
    asm_content = read_asm_from_7z_in_memory(input_asm_file)
    offsetlist_file = os.path.join(OUTPUT_FEATURE_DIR, "example_offsetlist.json")
    feature_file = os.path.join(OUTPUT_FEATURE_DIR, "example_feature.csv")

    # Initialize the AssemblyController with the branch operations, use_op_asm flag, and selected sections.
    asmReader = AssemblyController(branch_operations, True, selected_sections)

    asm_metadata = asmReader.parseAsmCodes(asm_content)

    # Iterate over files with a progress bar
    for filename, file_info in asm_metadata.items():
        #json_output = json.dumps(file_info.op_asm_offset_list, indent=4)
        #os.makedirs(OUTPUT_FEATURE_DIR, exist_ok=True)
        #with open(offsetlist_file, "w") as json_file:
        #    json_file.write(json_output)

        with open(feature_file, mode='w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Opcode', 'SHA-256 Hash'])  # Header row
            for opcode, offsetlist in file_info.op_asm_offset_list.items():
                # Serialize the offset list consistently
                canonical_str = json.dumps(offsetlist, separators=(',', ':'), sort_keys=True)
                # Compute SHA-256 hash
                hash_digest = hashlib.sha256(canonical_str.encode('utf-8')).hexdigest()
                # Write to CSV
                writer.writerow([opcode, hash_digest])

        print(f"Saved all opcode hashes to {feature_file}")

    print("Finished processing.")

if __name__ == "__main__":
    main()