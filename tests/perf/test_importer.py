import os
import sys
import time
from pathlib import Path

from tests.perf.generate_files_to_import import generate_modules


def test_importer_perf() -> None:
    # This is ran from pytest, which will have enabled the import mod
    modules_path = Path(__file__).parent / "generated_modules"
    if not modules_path.exists():
        generate_modules(modules_path, 1000)
    start_time = time.time()

    import generated_modules.import_generated_modules as import_generated_modules  # noqa

    end_time = time.time()

    assert end_time - start_time < 0.75, (
        "Importing 1000 modules should take less than 0.75s, took "
        f"{end_time - start_time:.2f}s"
    )


if __name__ == "__main__":
    os.environ["MEASURE_TIMES"] = "1"
    if len(sys.argv) > 1 and sys.argv[1] == "--megamock":
        from megamock import start_import_mod

        start_import_mod()

    start_time = time.time()

    import generated_modules.import_generated_modules as import_generated_modules

    end_time = time.time()

    print(
        f"Imported and executed {import_generated_modules.num_modules} modules "
        f"in {end_time - start_time:.2f} seconds"
    )

    from megamock.import_machinery import perf_stats

    print(perf_stats)
