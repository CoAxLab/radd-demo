#!usr/bin/env python
import os
import glob
modules = glob.glob(os.path.dirname(__file__) + "/*.py")
__all__ = [os.path.basename(f)[:-3] for f in modules]

__version__ = '0.0.3'