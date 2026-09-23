#!/usr/bin/env python3
"""Tests for the recovery-only aggregator; no inference or fixture re-execution."""
import copy
import unittest

import audit_perf_baseline_001 as audit


class RecoveryAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.row = audit.lines(audit.RUNS['A'] / 'raw-results.jsonl')[0]

    def test_corrected_count_and_raw_unchanged(self):
        source = copy.deepcopy(self.row)
        ids, removed = audit.corrected_a(source)
        self.assertEqual(removed, 4)
        self.assertEqual(len(ids), 128)
        self.assertEqual(source, self.row)
        self.assertEqual(source['output_tokens'], 132)
        self.assertEqual(source['status'], 'OVER_OUTPUT')

    def test_never_remove_nonzero_prefix(self):
        row = copy.deepcopy(self.row)
        row['output_token_ids'][0] = 1
        with self.assertRaises(ValueError):
            audit.corrected_a(row)

    def test_progress_count_must_match(self):
        row = copy.deepcopy(self.row)
        row['prompt_progress'].pop()
        with self.assertRaises(ValueError):
            audit.corrected_a(row)

    def test_reused_cache_is_rejected(self):
        row = copy.deepcopy(self.row)
        row['native_final']['timings']['cache_n'] = 1
        with self.assertRaises(ValueError):
            audit.corrected_a(row)

    def test_short_output_not_filled(self):
        row = copy.deepcopy(self.row)
        row['native_final']['tokens_predicted'] = 127
        row['native_final']['timings']['predicted_n'] = 127
        with self.assertRaises(ValueError):
            audit.corrected_a(row)

    def test_incomplete_request_rejected(self):
        row = copy.deepcopy(self.row)
        row['complete'] = False
        with self.assertRaises(ValueError):
            audit.corrected_a(row)

    def test_ignore_eos_change_rejected(self):
        row = copy.deepcopy(self.row)
        row['native_final']['generation_settings']['ignore_eos'] = True
        with self.assertRaises(ValueError):
            audit.corrected_a(row)

    def test_median_not_best_of(self):
        self.assertEqual(audit.stats([3, 1, 2]),
                         {'n': 3, 'median': 2, 'min': 1, 'max': 3, 'values': [3, 1, 2]})

    def test_empty_series_rejected(self):
        with self.assertRaises(ValueError):
            audit.stats([])

    def test_actual_canonical_set_and_client_gaps(self):
        result, rows, _ = audit.build()
        self.assertEqual(len(rows), 16)
        self.assertEqual(sum(r['measured'] for r in rows), 12)
        self.assertTrue(all(r['ttft_observed_s'] is None for r in rows))
        self.assertTrue(all(r['post_first_token_client_rate_tps'] is None for r in rows))
        self.assertTrue(all(c['request_latency_ratio'] is None for c in result['comparison'].values()))
        self.assertEqual(result['gates']['METRICS_COMPARABLE'], 'PARTIAL_ENGINE_DECODE_ONLY')


if __name__ == '__main__':
    unittest.main(verbosity=2)
