import re
import networkx as nx
import yaml
import io

from collections import defaultdict
from ARM_InstructionLayout import ArmFileInfo, ArmCodeBlock

k_file_format = 'file format'
k_section = 'section'
k_code_blocks = 'code_blocks'
k_address = 'address'
k_label = 'label'
k_op_address = 'op_address'
k_op_branch = 'op_branch'
k_op_opcode = 'op_code'
k_op_asm = 'op_asm'
k_instructions = 'instructions'
k_target_addr = 'target_addr'

class AssemblyController:
    def __init__(self, branch_ops, used_op_asm=True, selected_sections=None):
        self.cfg = nx.DiGraph()
        self.branch_ops = branch_ops
        self.used_op_asm = used_op_asm
        self.selected_sections = selected_sections
        self.op2cb = defaultdict(set)
        self.op2branch = defaultdict(set)
        self.cbset = set()
        self.branchset = set()

    @staticmethod
    def extract_filename_and_type(line_parts):
        """
        Extract filename and file type from a formatted string.
        """
        file_name = line_parts[0].replace('/', '=').replace('\\', '=')
        file_name_parts = file_name.split('=')
        file_name_meta = f"{file_name_parts[1]}_{file_name_parts[3]}_{file_name_parts[2]}"
        match = re.search(r'file format\s+(\S+)', line_parts[1])
        file_type = match.group(1) if match else ''
        return file_name_meta, file_type

    @staticmethod
    def extract_section_name(input_string):
        """
        Extract section name from a disassembly header line.
        """
        match = re.search(r'Disassembly of section ([\w\.\-]+):', input_string)
        return match.group(1) if match else None

    @staticmethod
    def extract_address_and_label(input_string):
        """
        Extract address and label name from a formatted assembly line.
        """
        match = re.match(r'([0-9A-Fa-f]+)\s+<([^>]+)>:', input_string)
        if match:
            return int(match.group(1), 16), match.group(2)
        return None, None

    def parse_branch_instruction(self, asm_line):
        """
        Parse a branch instruction to extract relevant details.
        """
        pattern = re.compile(
            r"\s*(?P<address>[0-9a-f]+):\s+(?P<op>[0-9a-f ]+)\s+(?P<op_asm>[a-z.]+)\s+(?P<target_addr>[0-9a-f]+)?(?:\s+<(?P<label>.+)>)?"
        )
        match = pattern.match(asm_line)
        if match and match.group("op_asm") in self.branch_ops:
            return {
                "address": int(match.group("address"), 16),
                "op": match.group("op"),
                "op_asm": match.group("op_asm"),
                "target_addr": int(match.group("target_addr"), 16) if match.group("target_addr") else 0,
                "label": match.group("label") or ''
            }
        return None

    def parse_asm_line(self, line):
        """
        Parse a single assembly instruction line.
        """
        op_address = int(line.split(':')[0].strip(), 16)
        parts = line.split('\t')
        op_code = parts[1].strip() if len(parts) > 1 else ''
        op_asm = ' '.join(parts[2:]).strip() if len(parts) > 2 else ''
        comment_parts = line.split('@ ')
        op_comment = comment_parts[1] if len(comment_parts) > 1 else ''
        op_branch = self.parse_branch_instruction(line)
        return op_address, op_code, op_asm, op_comment, op_branch

    def update_region(self, region_tuple, current_instruction):
        """
        Updates the region tuple based on the current instruction's offsets and branch target offsets.
        Ensures the region tuple contains the min and max of op_offset and branch.b_target_offset.
        """
        if not region_tuple:
            if current_instruction.branch:
                return (
                    current_instruction.op_offset,
                    current_instruction.op_offset,
                    current_instruction.branch.b_target_offset,
                    current_instruction.branch.b_target_offset,
                    current_instruction,
                )
            else:
                return (
                    current_instruction.op_offset,
                    current_instruction.op_offset,
                    0,
                    0,
                    current_instruction,
                )
        else:
            min_op_offset = min(region_tuple[0], current_instruction.op_offset)
            max_op_offset = max(region_tuple[1], current_instruction.op_offset)
            min_b_target_offset = min(region_tuple[2], current_instruction.branch.b_target_offset) if current_instruction.branch else region_tuple[2]
            max_b_target_offset = max(region_tuple[3], current_instruction.branch.b_target_offset) if current_instruction.branch else region_tuple[3]
            return (min_op_offset, max_op_offset, min_b_target_offset, max_b_target_offset, current_instruction)

    def update_asm_meta(self, current_file_info, current_cb, op_asm_keyword, current_instruction):
        file_info = current_file_info
        file_info.op_asm_offset_list.setdefault(op_asm_keyword, [])
        if current_instruction.branch:
            file_info.op_asm_offset_list[op_asm_keyword].append((current_cb.cb_offset, current_instruction.op_offset, current_instruction.branch.b_target_offset))
        else:
            file_info.op_asm_offset_list[op_asm_keyword].append((current_cb.cb_offset, current_instruction.op_offset, 0))

    def update_asm_meta_coverage(self, op_asm_keyword, cb_address, op_branch):
        self.op2cb[op_asm_keyword].add(cb_address)
        self.cbset.add(cb_address)
        if op_branch:
            self.op2branch[op_asm_keyword].add(op_branch['target_addr'])
            self.branchset.add(op_branch['target_addr'])

    def parseAsmCodes(self, asm_content):
        """
        Parse the assembly content (as a string) and identify basic blocks.
        """
        asm_meta = {}
        cur_section_name, file_name, file_type = '', '', ''
        first_cb = None

        file = io.StringIO(asm_content)  # Create a file-like object from string
        current_file_info, current_cb, current_section, last_cb = None, None, None, None
        op_address, last_op_address = 0, 0

        for line in file:
            line = line.strip()
            if not line:
                continue

            line_parts = [part.strip() for part in line.split(':')]
            if len(line_parts) > 1 and k_file_format in line_parts[1]:
                file_name, file_type = self.extract_filename_and_type(line_parts)
                asm_meta[file_name] = ArmFileInfo(file_name, file_type)
                current_file_info = asm_meta[file_name]
                continue

            if k_section in line and '<' not in line and '>:' not in line:
                cur_section_name = self.extract_section_name(line)
                current_section = None
                if not self.selected_sections or cur_section_name in self.selected_sections:
                    current_section = current_file_info.add_section(cur_section_name)
                continue

            if not current_section:
                continue

            if '<' in line and '>:' in line:
                cb_address, cb_label = self.extract_address_and_label(line)
                if cb_address >= 0 and cb_label:
                    last_cb = current_cb
                    if not first_cb:
                        current_section.section_addr = cb_address 
                    current_cb = ArmCodeBlock(cb_address, cb_label, current_section, last_cb)
                    if not first_cb:
                        first_cb = current_cb
                    current_section.add_code_block(cb_address, cb_label, current_cb)
                continue

            if line.count('\t') >= 3:
                last_op_address = op_address
                op_address, op_code, op_asm, op_comment, op_branch = self.parse_asm_line(line)
                current_instruction = current_file_info.sections[cur_section_name].code_blocks[cb_address].add_instruction(
                    op_address, op_code, op_asm, op_comment, op_branch
                )
                op_asm_keyword = op_asm.split(' ')[0] if self.used_op_asm else op_code.replace(' ', '')
                if op_asm_keyword == '@' and '<UNDEFINED>' in op_asm.split(' '):
                    continue
                self.update_asm_meta(current_file_info, current_cb, op_asm_keyword, current_instruction)

        if current_cb and last_cb:
            current_cb.cb_size = current_cb.cb_address - last_cb.cb_address

        return asm_meta

    def parseAsmForOpcodeFileName(self, file_path):
        """
        Parse the assembly file and identify basic blocks.
        """
        with open(file_path, 'r') as file:
            current_file_info, current_cb, current_section, last_cb = None, None, None, None
            op_address, last_op_address = 0, 0

            for line in file:
                line = line.strip()
                if not line:
                    continue

                line_parts = [part.strip() for part in line.split(':')]
                if len(line_parts) > 1 and k_file_format in line_parts[1]:
                    file_name, file_type = self.extract_filename_and_type(line_parts)
                    break
        return file_name

    def parseAsmForOpcodeCoverageRate(self, file_path, progress):
        """
        Parse the assembly file and identify basic blocks.
        """
        asm_meta = {}
        coverage_meta = {"cb_coverage": {}, "branch_coverage": {}}
        cur_section_name, file_name, file_type = '', '', ''
        first_cb = None

        with open(file_path, 'r') as file:
            lines = file.readlines()
            total_lines = len(lines)

            current_file_info, current_cb, current_section, last_cb = None, None, None, None
            op_address, last_op_address = 0, 0

            for idx, line in enumerate(lines):
                if progress:
                    progress(idx + 1, total_lines)

                line = line.strip()
                if not line:
                    continue

                line_parts = [part.strip() for part in line.split(':')]
                if len(line_parts) > 1 and k_file_format in line_parts[1]:
                    file_name, file_type = self.extract_filename_and_type(line_parts)
                    asm_meta['arm_info'] = ArmFileInfo(file_name, file_type)
                    current_file_info = asm_meta['arm_info']
                    continue

                if k_section in line and '<' not in line and '>:' not in line:
                    cur_section_name = self.extract_section_name(line)
                    current_section = None
                    if not self.selected_sections or cur_section_name in self.selected_sections:
                        current_section = current_file_info.add_section(cur_section_name)
                    continue

                if not current_section:
                    continue

                if '<' in line and '>:' in line:
                    cb_address, cb_label = self.extract_address_and_label(line)
                    if cb_address >= 0 and cb_label:
                        last_cb = current_cb
                        if not first_cb:
                            current_section.section_addr = cb_address 
                        current_cb = ArmCodeBlock(cb_address, cb_label, current_section, last_cb)
                        if not first_cb:
                            first_cb = current_cb
                        current_section.add_code_block(cb_address, cb_label, current_cb)
                    continue

                if line.count('\t') >= 3:
                    last_op_address = op_address
                    op_address, op_code, op_asm, op_comment, op_branch = self.parse_asm_line(line)
                    op_asm_keyword = op_asm.split(' ')[0] if self.used_op_asm else op_code.replace(' ', '')
                    if op_asm_keyword == '@' and '<UNDEFINED>' in op_asm.split(' '):
                        continue
                    self.update_asm_meta_coverage(op_asm_keyword, cb_address, op_branch)

            if current_cb and last_cb:
                current_cb.cb_size = current_cb.cb_address - last_cb.cb_address

        for opcode, cbset in self.op2cb.items():
            diff = self.cbset - cbset
            coverage_meta["cb_coverage"][opcode] = len(diff) / len(self.cbset)
        for opcode, branchset in self.op2branch.items():
            diff = self.branchset - branchset
            coverage_meta["branch_coverage"][opcode] = len(diff) / len(self.branchset)
        return file_name, coverage_meta
    
    def process_files(self, files):
        """
        Process multiple assembly files.
        """
        asm_files = {}
        for file in files:
            asm_files[file] = self.parseAsmCodes(file, asm_files)
        return asm_files