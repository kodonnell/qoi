import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
import pytest
import qoi
from PIL import Image


@pytest.mark.xfail(sys.platform == "win32", reason="not sure why this fails on windows ...")
def test_handles_ro_array_issue26():
    image_filepath = Path(__file__).parent.parent / "src" / "qoi" / "koi.png"
    image = Image.open(image_filepath).convert("RGB")
    image_qoi = np.asarray(image)  # NB: using np.array make it RW as it takes a copy
    assert not image_qoi.flags["WRITEABLE"]
    with NamedTemporaryFile() as f:
        _ = qoi.write(f.name, image_qoi)
