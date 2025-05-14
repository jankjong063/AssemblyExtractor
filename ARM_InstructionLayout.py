from collections import defaultdict
import json

class ArmInstruction:
    """
    Represents a single ARM instruction.
    """
    def __init__(self, op_address, op_opcode, op_asm, op_comment, branch=None, section=None, base_cb=None):
        self.base_cb = base_cb
        self.cb_address = self.base_cb.cb_address if self.base_cb else 0
        self.bb_offset = self.base_cb.cb_address - section.section_addr if self.base_cb else 0
        
        self.op_address = op_address
        self.op_offset = op_address - self.cb_address
        self.op_opcode = int(op_opcode.strip().replace(' ', ''), 16) if op_opcode.strip() else 0
        self.op_asm = op_asm
        self.op_opcode_asm = op_asm.split(' ')[0]
        self.op_comment = op_comment
        self.branch = branch
        self.section = section

class ArmBranch:
    """
    Represents a branch instruction in ARM.
    """
    def __init__(self, b_address, b_opcode, b_asm, b_target_addr, b_label, base_cb=None):
        self.base_cb = base_cb
        self.cb_address = self.base_cb.cb_address if self.base_cb else 0
        self.b_offset = b_address - self.cb_address
        self.b_target_offset = b_target_addr - self.cb_address
        
        self.b_address = b_address
        self.b_opcode = int(b_opcode.strip().replace(' ', ''), 16) if b_opcode.strip() else 0
        self.b_asm = b_asm
        self.b_opcode_asm = b_asm.split(' ')[0]
        self.b_target_addr = b_target_addr
        self.b_label = b_label

class ArmCodeBlock:
    """
    Represents a code block containing ARM instructions.
    """
    def __init__(self, cb_address, cb_label, section, last_cb):
        self.section = section
        self.cb_address = cb_address
        self.cb_label = cb_label
        self.cb_offset = cb_address - section.section_addr
        self.cb_size = 0
        self.last_cb = last_cb
        self.instructions = []
        self.instructions_count = 0
        self.branches = []
        self.branches_count = 0
        self.op_asm_total_count = 0
        self.op_asm_count = defaultdict(int)
        self.op_asm_offset_list = {}

        if self.last_cb:
            self.last_cb.cb_size = cb_address - self.last_cb.cb_address

    def add_instruction(self, op_address, op_opcode, op_asm, op_comment, op_branch):
        branch = None
        if op_branch and op_branch["address"] != -1:
            branch = ArmBranch(
                b_address=op_branch["address"],
                b_opcode=op_branch["op"],
                b_asm=op_branch["op_asm"],
                b_target_addr=op_branch["target_addr"],
                b_label=op_branch["label"],
                base_cb=self
            )
            self.branches.append(branch)
            self.branches_count += 1
            self.section.increase_branches_count()

        instruction = ArmInstruction(op_address, op_opcode, op_asm, op_comment, branch, self.section, self)
        self.instructions.append(instruction)
        self.instructions_count += 1
        self.section.increase_instructions_count()

        return instruction

class ArmSection:
    """
    Represents a section in the ARM assembly file.
    """
    def __init__(self, section_name):
        self.section_name = section_name
        self.section_addr = 0
        self.code_blocks_count = 0
        self.code_blocks = {}
        self.total_cb_instructions_count = 0
        self.total_b_branches_count = 0
        self.op_asm_total_count = 0
        self.op_asm_count = defaultdict(int)
        self.op_asm_offset_list = {}

    def increase_instructions_count(self):
        self.total_cb_instructions_count += 1

    def increase_branches_count(self):
        self.total_b_branches_count += 1

    def add_code_block(self, cb_address, cb_label, code_block):
        if cb_address in self.code_blocks:
            raise KeyError(f"Code block with address {cb_address} already exists.")
        self.code_blocks[cb_address] = code_block
        self.code_blocks_count = len(self.code_blocks)

    def get_code_blocks_count(self):
        return self.code_blocks_count

class ArmFileInfo:
    """
    Represents an ARM assembly file containing multiple sections.
    """
    def __init__(self, file_name, file_type):
        self.file_name = file_name
        self.file_type = file_type
        self.sections_count = 0
        self.sections = {}
        self.sections_addrs = {}
        #self.op_asm_total_count = 0
        #self.op_asm_count = defaultdict(int)
        self.op_asm_offset_list = {}

    def add_section(self, section_name):
        if section_name not in self.sections:
            self.sections[section_name] = ArmSection(section_name)
            self.sections_count = len(self.sections)
        return self.sections[section_name]
  
