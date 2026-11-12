#!/usr/bin/env python3
"""Summarize selected Wine Vulkan events without echoing raw log text.

No debugger, launch, file mutation, or third-party dependencies. A count of zero
means 'not found in this input', not proof that an operation never happened.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

PREFIX = re.compile(r"^(?:\d+(?:\.\d+)?:)?(?P<pid>[0-9a-fA-F]{4,}):[0-9a-fA-F]{4,}:")
CREATE = re.compile(r'wine_vkCreateDevice Device name:\s*"([^"]*)"')
NULL_RESET = re.compile(r'thunk(?:32|64)_vkResetCommandPool\s+(?:\(nil\)|0x0+),\s*(?:0x0+|0),\s*0\b')
ENUM = re.compile(r'wine_vkEnumeratePhysicalDevices Returning (\d+) devices\.')


def normalize_pid(value):
    if not re.fullmatch(r'(?:0x)?[0-9a-fA-F]{1,16}', value):
        raise ValueError('Wine PID must be hexadecimal, for example 0504 or 0x504')
    return int(value, 16)


def device_class(name):
    """Fixed labels only: never print arbitrary text extracted from a log."""
    lowered = name.lower()
    if 'llvmpipe' in lowered or 'lavapipe' in lowered:
        return 'software (llvmpipe/lavapipe)'
    if 'radeon' in lowered and 'radv' in lowered:
        return 'AMD Radeon (RADV)'
    return 'other or unclassified'


def summarize(lines, pid=None):
    processes = {}
    for line in lines:
        match = PREFIX.match(line)
        if not match:
            continue
        found_pid = int(match['pid'], 16)
        if pid is not None and found_pid != pid:
            continue
        creation = CREATE.search(line)
        enumeration = ENUM.search(line)
        null_reset = NULL_RESET.search(line)
        created = 'wine_vkCreateDevice Created device ' in line
        if not (creation or enumeration or null_reset or created):
            continue
        key = f'{found_pid:04x}'
        state = processes.setdefault(key, {
            'device_creation_requests_by_class': Counter(),
            'device_created_messages': 0,
            'enumerated_device_counts': Counter(),
            'null_device_and_pool_resets': 0,
        })
        if creation:
            state['device_creation_requests_by_class'][device_class(creation[1])] += 1
        if enumeration:
            # Keep arbitrary input from growing output without bound.
            number = int(enumeration[1]) if len(enumeration[1]) <= 4 else 10000
            state['enumerated_device_counts'][str(number) if number <= 64 else '>64'] += 1
        if null_reset:
            state['null_device_and_pool_resets'] += 1
        if created:
            state['device_created_messages'] += 1
    return {
        'scope': 'Selected messages in this input only; not a diagnosis or complete API trace.',
        'processes': processes,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    parser.add_argument('--pid', help='Wine hexadecimal PID, NOT the Linux host PID')
    args = parser.parse_args()
    try:
        pid = normalize_pid(args.pid) if args.pid is not None else None
        with args.log.open(encoding='utf-8', errors='replace') as source:
            result = summarize(source, pid)
    except (OSError, ValueError) as exc:
        # No raw log text in errors, either.
        parser.exit(2, f'Unable to summarize log: {type(exc).__name__}. Check input path/PID.\n')
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
