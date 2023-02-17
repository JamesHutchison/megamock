from megamock.custom_loader import ReferenceTrackerFinder
from .megapatches import MegaPatch
from .megamocks import MegaMock


import sys

sys.meta_path = [ReferenceTrackerFinder(sys.meta_path[:])]

__all__ = ["MegaPatch", "MegaMock"]
