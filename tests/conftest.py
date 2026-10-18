# -*- coding: utf-8 -*-
import os
import tempfile

# Must happen before bowtally.config is imported anywhere.
os.environ["BOWTALLY_DATA_DIR"] = tempfile.mkdtemp(prefix="bowtally_test_")
