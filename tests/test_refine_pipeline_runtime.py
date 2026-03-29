import unittest

from ours.refine_pipeline_runtime import (
    configure_pipeline_offload,
    normalize_pipeline_offload_mode,
    resolve_pipeline_execution_device,
)


class FakePipe:
    def __init__(self) -> None:
        self.device = "cpu"
        self._execution_device = "cuda:0"
        self.calls: list[tuple[str, object]] = []

    def to(self, device):
        self.calls.append(("to", device))
        self.device = device
        self._execution_device = device
        return self

    def enable_model_cpu_offload(self, *, device):
        self.calls.append(("enable_model_cpu_offload", device))
        self._execution_device = device

    def enable_sequential_cpu_offload(self, *, device):
        self.calls.append(("enable_sequential_cpu_offload", device))
        self._execution_device = device


class RefinePipelineRuntimeTest(unittest.TestCase):
    def test_normalize_pipeline_offload_mode_uses_none_by_default(self) -> None:
        self.assertEqual(normalize_pipeline_offload_mode(None), "none")

    def test_normalize_pipeline_offload_mode_rejects_unknown_value(self) -> None:
        with self.assertRaisesRegex(ValueError, "refine_pipeline_offload_mode"):
            normalize_pipeline_offload_mode("gpu_only")

    def test_configure_pipeline_offload_keeps_legacy_to_cuda_path(self) -> None:
        pipe = FakePipe()
        logs: list[str] = []

        configured = configure_pipeline_offload(
            pipe,
            offload_mode="none",
            target_device="cuda",
            log_fn=logs.append,
        )

        self.assertIs(configured, pipe)
        self.assertEqual(pipe.calls, [("to", "cuda")])
        self.assertEqual(logs, ["开始执行 pipe.to(cuda)", "pipe.to(cuda) 返回"])

    def test_configure_pipeline_offload_uses_model_cpu_hook(self) -> None:
        pipe = FakePipe()
        logs: list[str] = []

        configured = configure_pipeline_offload(
            pipe,
            offload_mode="model_cpu",
            target_device="cuda",
            log_fn=logs.append,
        )

        self.assertIs(configured, pipe)
        self.assertEqual(pipe.calls, [("enable_model_cpu_offload", "cuda")])
        self.assertEqual(
            logs,
            [
                "开始启用 enable_model_cpu_offload(device=cuda)",
                "enable_model_cpu_offload 返回",
            ],
        )

    def test_configure_pipeline_offload_uses_sequential_cpu_hook(self) -> None:
        pipe = FakePipe()
        logs: list[str] = []

        configured = configure_pipeline_offload(
            pipe,
            offload_mode="sequential_cpu",
            target_device="cuda",
            log_fn=logs.append,
        )

        self.assertIs(configured, pipe)
        self.assertEqual(pipe.calls, [("enable_sequential_cpu_offload", "cuda")])
        self.assertEqual(
            logs,
            [
                "开始启用 enable_sequential_cpu_offload(device=cuda)",
                "enable_sequential_cpu_offload 返回",
            ],
        )

    def test_resolve_pipeline_execution_device_prefers_execution_device(self) -> None:
        pipe = FakePipe()
        pipe.device = "cpu"
        pipe._execution_device = "cuda:1"

        self.assertEqual(resolve_pipeline_execution_device(pipe), "cuda:1")

    def test_resolve_pipeline_execution_device_falls_back_to_device(self) -> None:
        pipe = FakePipe()
        pipe._execution_device = None
        pipe.device = "cuda:2"

        self.assertEqual(resolve_pipeline_execution_device(pipe), "cuda:2")


if __name__ == "__main__":
    unittest.main()
