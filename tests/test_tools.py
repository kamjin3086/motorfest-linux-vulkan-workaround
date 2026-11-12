"""Synthetic fixtures only; no original logs or account data."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('summary', ROOT/'scripts/summarize-vulkan.py')
SUMMARY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUMMARY)

FIXTURE = '''100.001:0504:0508:trace:vulkan:wine_vkEnumeratePhysicalDevices Returning 2 devices.
100.002:0504:0508:trace:vulkan:wine_vkCreateDevice Device name: "llvmpipe (LLVM test)".
100.003:0504:0508:trace:vulkan:wine_vkCreateDevice Created device 0x1234, host_device 0x5678.
100.004:0504:0508:trace:vulkan:wine_vkCreateDevice Device name: "AMD Radeon Example (RADV TEST)".
100.005:0504:0508:trace:vulkan:wine_vkCreateDevice Created device 0x3333, host_device 0x4444.
100.006:0504:05f0:trace:vulkan:thunk64_vkResetCommandPool (nil), 0x0, 0
100.007:0240:0300:trace:vulkan:thunk32_vkResetCommandPool (nil), 0x0, 0
100.008:0504:05f0:trace:vulkan:thunk64_vkResetCommandPool 0x1234, 0x0, 0
'''


class SummaryTests(unittest.TestCase):
    def test_failure_events_and_pid_filter(self):
        result = SUMMARY.summarize(FIXTURE.splitlines(), SUMMARY.normalize_pid('0x504'))
        self.assertEqual(list(result['processes']), ['0504'])
        game = result['processes']['0504']
        self.assertEqual(game['device_creation_requests_by_class']['software (llvmpipe/lavapipe)'], 1)
        self.assertEqual(game['device_creation_requests_by_class']['AMD Radeon (RADV)'], 1)
        self.assertEqual(game['device_created_messages'], 2)
        self.assertEqual(game['null_device_and_pool_resets'], 1)
        self.assertEqual(game['enumerated_device_counts'], {'2': 1})

    def test_all_pids_separated(self):
        self.assertEqual(set(SUMMARY.summarize(FIXTURE.splitlines())['processes']), {'0504', '0240'})

    def test_missing_is_not_failure(self):
        result = SUMMARY.summarize(['unrelated text', 'token=DO_NOT_ECHO'])
        self.assertEqual(result['processes'], {})
        self.assertNotIn('DO_NOT_ECHO', json.dumps(result))

    def test_arbitrary_paths_and_names_not_echoed(self):
        lines = ['1.001:0504:0508:trace:vulkan:wine_vkCreateDevice Device name: "PRIVATE_DEVICE_SECRET".',
                 '/synthetic/PRIVATE_USER/PRIVATE_TOKEN',
                 '1.002:0504:0508:trace:vulkan:some_other_event PRIVATE_TOKEN']
        text = json.dumps(SUMMARY.summarize(lines))
        self.assertNotIn('PRIVATE', text)
        self.assertIn('other or unclassified', text)

    def test_zero_spellings_and_nonzero_pool(self):
        lines = ['0504:0508:trace:vulkan:thunk64_vkResetCommandPool 0x0000, 0, 0',
                 '0504:0508:trace:vulkan:thunk64_vkResetCommandPool (nil), 0x1234, 0']
        state = SUMMARY.summarize(lines)['processes']['0504']
        self.assertEqual(state['null_device_and_pool_resets'], 1)

    def test_invalid_pid(self):
        for value in ('', '-1', '0504:0508', 'not-a-pid'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                SUMMARY.normalize_pid(value)

    def test_cli_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'input.txt'
            source.write_text(FIXTURE)
            before = source.read_bytes()
            run = subprocess.run([sys.executable, str(ROOT/'scripts/summarize-vulkan.py'), str(source), '--pid', '0504'], capture_output=True, text=True, check=True)
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(json.loads(run.stdout)['processes']['0504']['null_device_and_pool_resets'], 1)

    def test_cli_missing_input(self):
        run = subprocess.run([sys.executable, str(ROOT/'scripts/summarize-vulkan.py'), '/nonexistent/log'], capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertNotIn('Traceback', run.stderr)


class WrapperTests(unittest.TestCase):
    def test_requires_command(self):
        run = subprocess.run(['bash', str(ROOT/'scripts/run-radeon.sh')], capture_output=True)
        self.assertEqual(run.returncode, 2)

    def test_environment_scope_argument_preservation_and_exit_status(self):
        original = os.environ.get('VK_LOADER_DRIVERS_SELECT')
        code = 'import os,sys; print(os.environ["VK_LOADER_DRIVERS_SELECT"]); print(repr(sys.argv[1:])); sys.exit(7)'
        run = subprocess.run(['bash', str(ROOT/'scripts/run-radeon.sh'), sys.executable, '-c', code, 'space value', '*literal*', ''], capture_output=True, text=True)
        self.assertEqual(run.returncode, 7)
        self.assertEqual(run.stdout.splitlines(), ['radeon_icd*', "['space value', '*literal*', '']"])
        self.assertEqual(os.environ.get('VK_LOADER_DRIVERS_SELECT'), original)


if __name__ == '__main__':
    unittest.main()
