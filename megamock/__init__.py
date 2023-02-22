from megamock.custom_loader import ReferenceTrackerFinder
from .megapatches import MegaPatch
from .megamocks import MegaMock


def start_loader() -> None:
    """
    Start the MegaMock loader.

    This should be done as one of the first things when testing
    """
    import sys

    sys.meta_path = [ReferenceTrackerFinder(sys.meta_path[:])]


__all__ = ["MegaPatch", "MegaMock"]
