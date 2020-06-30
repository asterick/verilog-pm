#!/usr/bin/env python3

# ISC License
# 
# Copyright (c) 2019, Bryon Vandiver
# 
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
# 
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import os
import csv

DEFAULT_INSTRUCTION = "nop"
MICROCODE_FIELDS = ['label', 'condition', 'branch', 'set_pc', 'data_space', 'data_direction', 'data_bank', 'data_address', 'interruptable']

CONDITIONS = {
    "lt": "less_than",
    "le": "less_equal",
    "gt": "greater_than",
    "ge": "greater_equal",
    "v": "overflow",
    "nv": "not_overflow",
    "p": "positive",
    "m": "minus",
    "c": "carry",
    "nc": "not_carry",
    "z": "zero",
    "nz": "not_zero",

    "f0": "special_flag_0",
    "f1": "special_flag_1",
    "f2": "special_flag_2",
    "f3": "special_flag_3",
    "nf0": "not_special_flag_0",
    "nf1": "not_special_flag_1",
    "nf2": "not_special_flag_2",
    "nf3": "not_special_flag_3"
}

ARGUMENTS = {
    "ALL": "all",
    "ALE": "ale",

    "A": "a",
    "B": "b",
    "L": "l",
    "H": "h",

    "BA": "ba",
    "HL": "hl",

    "IX": "ix",
    "IY": "iy",
    "BR": "br",

    "NB": "nb",
    "EP": "ep",
    "XP": "xp",
    "YP": "yp",
    "IP": "ip",

    "PC": "pc",
    "SP": "sp",
    "SC": "sc",

    "[hhll]": "abs16",
    "[HL]": "absHL",
    "[IX]": "absIX",
    "[IY]": "absIY",
    "[SP+dd]": "dispSP",
    "[IX+dd]": "dispIX",
    "[IY+dd]": "dispIY",
    "[IX+L]": "offIX",
    "[IY+L]": "offIY",
    "[BR:ll]": "absBR",
    "[kk]": "vect",

    "rr": "rel8",
    "qqrr": "rel16",
    "#nn": "imm8",
    "#mmnn": "imm16"
}

op0s, op1s, op2s = [DEFAULT_INSTRUCTION] * 0x100, [DEFAULT_INSTRUCTION] * 0x100, [DEFAULT_INSTRUCTION] * 0x100

# Base operations
op0s[0xCE] = 'extend_ce'
op0s[0xCF] = 'extend_cf'
all_ops = {
    'extend_ce': [{
        'label': 'extend_ce',
        'branch': 'code1',
        'data_direction': 'read',
        'data_bank': 'cb',
        'data_address': 'pc',
        'data_space': 'code',
        'set_pc': 'increment'
    }],
    'extend_cf': [{
        'label': 'extend_cf',
        'branch': 'code2',
        'data_direction': 'read',
        'data_bank': 'cb',
        'data_address': 'pc',
        'data_space': 'code',
        'set_pc': 'increment'
    }]
}

def format(op, cycles, lead, *args):
    condition = None
    
    if args[0].lower() in CONDITIONS:
        condition, args = args[0].lower(), args[1:]
        condition_name = CONDITIONS[condition]

    args = [ARGUMENTS[arg] for arg in args if arg]

    if condition:    
        name = "_".join([op.lower(), condition.lower()] + args)
    else:
        name = "_".join([op.lower()] + args)

    cycles = [int(x) for x in cycles.split(",")]
    cond_true, cond_false = cycles[0] - lead, cycles[-1] - lead

    result = {
        'op': op.lower(),
        'args': args,
        'cycles': cond_true,
        'condition': None
    }

    if condition:
        result['condition'] = (condition.lower(), cond_false)

    return name, result

def build(name, op):
    op, args, cycles, condition = op['op'], op['args'], op['cycles'], op['condition']

    if op != 'ld' or args[0] != 'nb':
        interruptable = 'yes'
    else:
        interruptable = ''

    instructions = [{} for _ in range(cycles)]
    instructions[0]['label'] = name

    if condition:
        condition, cycles = condition
        instructions[cycles-1]['interruptable'] = interruptable
        instructions[cycles-1]['condition'] = condition

    # Setup pre-fetch for next instruction
    instructions[-1]['branch'] = 'code0'
    instructions[-1]['data_direction'] = 'read'
    instructions[-1]['data_bank'] = 'cb'
    instructions[-1]['data_address'] = 'pc'
    instructions[-1]['data_space'] = 'code'
    instructions[-1]['set_pc'] = 'increment'
    instructions[-1]['interruptable'] = interruptable

    return instructions

with open(os.path.join(os.path.dirname(__file__), 's1c88.csv'), 'r') as csvfile:
    spamreader = csv.reader(csvfile)

    next(spamreader)

    for row in spamreader:
        code, cycles0, op0, arg0_1, arg0_2, cycles1, op1, arg1_1, arg1_2, cycles2, op2, arg2_1, arg2_2 = row
        code = int(code, 16)

        if not op0 in ['[EXPANSION]', 'undefined']:
            name, op = format(op0, cycles0, 0, arg0_1, arg0_2)
            if name in all_ops:
                raise Exception("%s is already defined" % name)

            op0s[code] = name           
            all_ops[name] = build(name, op)
        if op1 != 'undefined':
            name, op = format(op1, cycles1, 1, arg1_1, arg1_2)
            if name in all_ops:
                raise Exception("%s is already defined" % name)

            op1s[code] = name
            all_ops[name] = build(name, op)
        if op2 != 'undefined':
            name, op = format(op2, cycles2, 1, arg2_1, arg2_2)
            if name in all_ops:
                raise Exception("%s is already defined" % name)

            op2s[code] = name
            all_ops[name] = build(name, op)

with open(os.path.join(os.path.dirname(__file__), 'jump_tbl.csv'), 'w') as csvfile:
    spamwriter = csv.writer(csvfile)
    spamwriter.writerow(['inst', 'inst_ce', 'inst_cf'])
    for i, op0 in enumerate(op0s):
        spamwriter.writerow([op0, op1s[i], op2s[i]])

with open(os.path.join(os.path.dirname(__file__), 'microcode.csv'), 'w') as csvfile:
    spamwriter = csv.writer(csvfile)
    spamwriter.writerow(MICROCODE_FIELDS)
    
    for name, built in all_ops.items():
        for row in built:
            spamwriter.writerow([row[col] if col in row else "" for col in MICROCODE_FIELDS])
