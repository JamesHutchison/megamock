from megamock.custom_loader import ReferenceTrackerFinder
from .megapatches import MegaPatch


import sys

sys.meta_path = [ReferenceTrackerFinder(sys.meta_path[:])]

__all__ = ["MegaPatch"]
