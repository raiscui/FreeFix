import unittest

from recon.refine_runtime import resolve_strategy_resume_step, resolve_strategy_step


class RefineRuntimeTest(unittest.TestCase):
    def test_payload_step_has_priority_when_checkpoint_records_real_step(self) -> None:
        self.assertEqual(
            resolve_strategy_resume_step(payload_step=34999, load_step=12000),
            34999,
        )

    def test_negative_payload_step_falls_back_to_load_step(self) -> None:
        self.assertEqual(
            resolve_strategy_resume_step(payload_step=-1, load_step=29999),
            29999,
        )

    def test_strategy_step_continues_original_training_timeline(self) -> None:
        resume_step = resolve_strategy_resume_step(payload_step=34999, load_step=12000)
        self.assertEqual(
            resolve_strategy_step(strategy_resume_step=resume_step, local_step=0),
            34999,
        )
        self.assertEqual(
            resolve_strategy_step(strategy_resume_step=resume_step, local_step=4),
            35003,
        )


if __name__ == "__main__":
    unittest.main()
