from megamock.custom_loader import WrapperFinder
from .megapatching import MegaPatch


import sys
import asttokens

sys.meta_path = [WrapperFinder(sys.meta_path[:])]

__all__ = ["MegaPatch"]
