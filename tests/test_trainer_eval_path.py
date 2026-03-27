import types
import unittest
from unittest.mock import patch

import torch

from recon.trainer import Runner


class TrainerEvalPathTest(unittest.TestCase):
    def test_rasterize_splats_w_certainty_uses_self_cfg(self) -> None:
        runner = Runner.__new__(Runner)
        runner.cfg = types.SimpleNamespace(
            sh_degree=3,
            near_plane=0.01,
            far_plane=1.0,
            c_exp_index=[0.1, 0.2],
        )
        runner.splats = {
            "means": torch.ones((1, 3), dtype=torch.float32, requires_grad=True),
            "quats": torch.ones((1, 4), dtype=torch.float32, requires_grad=True),
            "scales": torch.ones((1, 3), dtype=torch.float32, requires_grad=True),
            "opacities": torch.ones((1,), dtype=torch.float32, requires_grad=True),
            "features": torch.ones((1, 32), dtype=torch.float32, requires_grad=True),
            "colors": torch.ones((1, 3), dtype=torch.float32, requires_grad=True),
        }

        def fake_rasterize_splats(**kwargs):
            base = runner.splats["means"].sum()
            if kwargs.get("override_color") is not None:
                cert = kwargs["override_color"].mean()
                rgbs = cert.reshape(1, 1, 1, 1).expand(1, 1, 1, 3)
                alphas = torch.ones((1, 1, 1, 1), dtype=torch.float32)
                return rgbs, alphas, {}

            rgbs = torch.stack([base, base, base, base]).reshape(1, 1, 1, 4)
            alphas = torch.ones((1, 1, 1, 1), dtype=torch.float32)
            return rgbs, alphas, {}

        runner.rasterize_splats = fake_rasterize_splats

        colors, multi_certainties, alphas, depths = Runner.rasterize_splats_w_certainty(
            runner,
            camtoworlds=torch.eye(4, dtype=torch.float32)[None],
            Ks=torch.eye(3, dtype=torch.float32)[None],
            width=1,
            height=1,
        )

        self.assertEqual(tuple(colors.shape), (1, 1, 3))
        self.assertEqual(len(multi_certainties), 2)
        self.assertEqual(tuple(alphas.shape), (1, 1))
        self.assertEqual(tuple(depths.shape), (1, 1, 1))

    def test_rasterize_splats_skips_app_module_when_override_color_is_given(self) -> None:
        runner = Runner.__new__(Runner)
        runner.cfg = types.SimpleNamespace(
            app_opt=True,
            sh_degree=3,
            antialiased=False,
            packed=False,
            absgrad=False,
            sparse_grad=False,
        )
        runner.splats = {
            "means": torch.ones((1, 3), dtype=torch.float32),
            "quats": torch.ones((1, 4), dtype=torch.float32),
            "scales": torch.zeros((1, 3), dtype=torch.float32),
            "opacities": torch.zeros((1,), dtype=torch.float32),
            "features": torch.ones((1, 32), dtype=torch.float32),
            "colors": torch.ones((1, 3), dtype=torch.float32),
        }

        class ShouldNotBeCalled:
            def __call__(self, *args, **kwargs):
                raise AssertionError("app_module should be bypassed when override_color is provided")

        runner.app_module = ShouldNotBeCalled()

        fake_render_colors = torch.ones((1, 1, 1, 3), dtype=torch.float32)
        fake_render_alphas = torch.ones((1, 1, 1, 1), dtype=torch.float32)

        with patch("recon.trainer.rasterization", return_value=(fake_render_colors, fake_render_alphas, {})):
            render_colors, render_alphas, _ = Runner.rasterize_splats(
                runner,
                camtoworlds=torch.eye(4, dtype=torch.float32)[None],
                Ks=torch.eye(3, dtype=torch.float32)[None],
                width=1,
                height=1,
                override_color=torch.ones((1, 3), dtype=torch.float32),
                sh_degree=None,
            )

        self.assertTrue(torch.equal(render_colors, fake_render_colors))
        self.assertTrue(torch.equal(render_alphas, fake_render_alphas))


if __name__ == "__main__":
    unittest.main()
