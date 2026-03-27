import json
import tempfile
import unittest
from pathlib import Path

import imageio.v2 as imageio
import numpy as np

from recon.datasets.colmap import Dataset


class FakeParser:
    """用于构造最小 Dataset 契约测试的假 parser。"""

    def __init__(
        self,
        image_paths: list[str],
        image_names: list[str],
        test_every: int = 8,
    ):
        self.image_paths = image_paths
        self.image_names = image_names
        self.test_every = test_every
        self.camera_ids = ["cam0"] * len(image_paths)
        self.Ks_dict = {"cam0": np.eye(3, dtype=np.float32)}
        self.params_dict = {"cam0": np.array([], dtype=np.float32)}
        self.camtoworlds = np.stack(
            [np.eye(4, dtype=np.float32) for _ in image_paths],
            axis=0,
        )


class ColmapDatasetContractTest(unittest.TestCase):
    def _make_fake_images(
        self,
        pixel_values: tuple[int, ...],
    ) -> tuple[list[str], list[str]]:
        """构造一组最小图片, 让测试只关注 Dataset 行为本身。"""
        image_paths: list[str] = []
        image_names: list[str] = []

        for index, pixel_value in enumerate(pixel_values):
            image_name = f"{index:03d}.png"
            image_path = self.tmp_path / image_name
            image = np.full((3, 4, 3), pixel_value, dtype=np.uint8)
            imageio.imwrite(image_path, image)
            image_paths.append(str(image_path))
            image_names.append(image_name)

        return image_paths, image_names

    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_dataset_returns_render_traj_metadata_fields(self) -> None:
        # 用临时目录造两张最小图片, 避免测试依赖真实大数据集。
        image_paths, image_names = self._make_fake_images((32, 196))

        partition_path = self.tmp_path / "partition.json"
        partition_path.write_text(
            json.dumps({"train": [0], "test": [1]}),
            encoding="utf-8",
        )

        dataset = Dataset(
            parser=FakeParser(image_paths=image_paths, image_names=image_names),
            split="test",
            partition_file=str(partition_path),
        )

        sample = dataset[0]

        # `render_traj` 会直接消费这些字段。
        # 这里显式断言, 防止以后再出现字段契约回退。
        self.assertEqual(sample["image_path"], image_paths[1])
        self.assertEqual(sample["image_name"], image_names[1])
        self.assertEqual(sample["image_size"], (4, 3))
        self.assertEqual(tuple(sample["image"].shape), (3, 4, 3))

    def test_dataset_fallback_split_excludes_test_samples_from_train(self) -> None:
        # 没有 partition.json 时, 仍应保证 train/test 互斥。
        image_paths, image_names = self._make_fake_images((16, 32, 64, 128))
        parser = FakeParser(
            image_paths=image_paths,
            image_names=image_names,
            test_every=2,
        )

        train_dataset = Dataset(parser=parser, split="train", partition_file=None)
        test_dataset = Dataset(parser=parser, split="test", partition_file=None)

        # test_every=2 时, test 取偶数位, train 取剩余奇数位。
        self.assertEqual(train_dataset.indices.tolist(), [1, 3])
        self.assertEqual(test_dataset.indices.tolist(), [0, 2])
        self.assertTrue(set(train_dataset.indices).isdisjoint(test_dataset.indices))


if __name__ == "__main__":
    unittest.main()
