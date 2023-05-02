import sys
import time

if len(sys.argv) > 1 and sys.argv[1] == "--megamock":
    from megamock import start_import_mod

    start_import_mod()

start_time = time.time()

import generated_modules.import_generated_modules as import_generated_modules

end_time = time.time()

print(
    f"Imported and executed {import_generated_modules.num_modules} modules in {end_time - start_time:.2f} seconds"
)

from megamock.import_machinery import perf_stats

print(perf_stats)
