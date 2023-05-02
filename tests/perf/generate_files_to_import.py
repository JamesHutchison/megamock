import os
import textwrap
from pathlib import Path


def create_subdirectory(subdir):
    if not os.path.exists(subdir):
        os.makedirs(subdir)


def generate_module(subdir, module_name, content):
    with open(os.path.join(subdir, f"{module_name}.py"), "w") as f:
        f.write(content)


def generate_import_script(subdir, num_modules):
    with open(os.path.join(subdir, "import_generated_modules.py"), "w") as f:
        f.write("import sys\n")
        f.write(f"sys.path.append('{os.path.abspath(subdir)}')\n\n")
        for i in range(num_modules):
            module_name = f"generated_module_{i}"
            f.write(
                f"from {module_name} import hello_{module_name}, a_var_{module_name}\n"
            )
        f.write("\n")
        f.write("def run_all_generated_modules():\n")
        for i in range(num_modules):
            f.write(f"    hello_generated_module_{i}()\n")
        f.write(f"num_modules = {num_modules}\n")


def generate_modules(subdir, num_modules):
    create_subdirectory(subdir)
    for i in range(num_modules):
        module_name = f"generated_module_{i}"
        content = f"""
            def hello_{module_name}():
                print("Hello from {module_name}!")

            a_var_{module_name} = 1
        """
        # remove leading indents using textwrap.dedent
        content = textwrap.dedent(content)
        generate_module(subdir, module_name, content)
    generate_import_script(subdir, num_modules)


if __name__ == "__main__":
    num_modules = 1000  # Specify the number of modules to generate
    subdir = Path(__file__).parent / "generated_modules"
    generate_modules(subdir, num_modules)
