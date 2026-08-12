import os
import tempfile
import unittest

import numpy as np

from backend.main import load_image_from_upload_bytes


class MhaUploadTests(unittest.TestCase):
    def test_loads_mha_image_bytes(self):
        try:
            import SimpleITK as sitk
        except ImportError:
            self.skipTest("SimpleITK non installé")

        image = sitk.GetImageFromArray(np.arange(16, dtype=np.float32).reshape(4, 4))
        with tempfile.NamedTemporaryFile(suffix=".mha", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            sitk.WriteImage(image, tmp_path)
            with open(tmp_path, "rb") as fh:
                payload = fh.read()

            loaded = load_image_from_upload_bytes(payload, "sample.mha")
            self.assertIsInstance(loaded, np.ndarray)
            self.assertEqual(loaded.ndim, 3)
            self.assertEqual(loaded.shape[2], 3)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()
