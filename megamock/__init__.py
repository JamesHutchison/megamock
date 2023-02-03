from megamock.custom_loader import ReferenceTrackerFinder
from .megapatching import MegaPatch


import sys

sys.meta_path = [ReferenceTrackerFinder(sys.meta_path[:])]

__all__ = ["MegaPatch"]
