use defaultdict::DefaultHashMap;
use once_cell::sync::Lazy;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PySet, PyTuple};
use std::collections::{HashMap, HashSet};
use std::sync::{Mutex, MutexGuard};

#[derive(Eq, Hash, PartialEq, Debug, Clone)]
struct ModAndName {
    module: String,
    name: String,
}

impl IntoPy<PyObject> for ModAndName {
    fn into_py(self, _py: Python) -> PyObject {
        Python::with_gil(|py| {
            let module_obj = self.module.into_py(py);
            let name_obj = self.name.into_py(py);

            PyTuple::new(py, vec![module_obj, name_obj]).into()
        })
    }
}

#[pyclass]
struct References {
    references: DefaultHashMap<String, HashMap<String, ModAndName>>,
    reverse_references: DefaultHashMap<String, DefaultHashMap<String, HashSet<ModAndName>>>,
    renames: HashMap<ModAndName, String>,
}

static mut REFERENCES_SINGLETON: Lazy<Mutex<References>> =
    Lazy::new(|| Mutex::new(References::new()));

fn get_instance() -> MutexGuard<'static, References> {
    unsafe { REFERENCES_SINGLETON.lock().unwrap() }
}

#[pymethods]
impl References {
    #[new]
    fn new() -> References {
        References {
            references: DefaultHashMap::new(),
            reverse_references: DefaultHashMap::new(),
            renames: HashMap::new(),
        }
    }

    #[staticmethod]
    pub fn add_reference(
        module: &PyAny,
        calling_module: &PyAny,
        original_name: &str,
        named_as: &str,
    ) -> PyResult<()> {
        let instance = &mut get_instance();
        let module_path = module
            .getattr("__name__")
            .unwrap()
            .extract::<String>()
            .unwrap();
        let mod_and_name = ModAndName {
            module: module_path.clone(),
            name: original_name.to_owned(),
        };

        let calling_module_name = calling_module
            .getattr("__name__")
            .unwrap()
            .extract::<String>()
            .unwrap();
        let references = &mut instance.references;
        let references_entry = references.get_mut(&calling_module_name);
        references_entry.insert(named_as.to_owned(), mod_and_name);

        let base_original_name = original_name.split('.').next().unwrap().to_owned();
        let reverse_references = &mut instance.reverse_references;
        let reverse_references_entry = reverse_references.get_mut(&module_path);
        let set = reverse_references_entry.get_mut(&base_original_name);
        set.insert(ModAndName {
            module: calling_module_name.clone(),
            name: named_as.to_owned(),
        });

        if original_name != named_as {
            let renames_dict = &mut instance.renames;
            renames_dict.insert(
                ModAndName {
                    module: calling_module_name.clone(),
                    name: named_as.to_owned(),
                },
                original_name.to_owned(),
            );
        }

        Ok(())
    }

    #[staticmethod]
    pub fn get_references(module_name: &str, named_as: &str) -> PyResult<PyObject> {
        let references = &get_instance().references;
        let module_name_str = module_name.to_owned();
        if !references.contains_key(&module_name_str) {
            return Python::with_gil(|py| Ok(PySet::empty(py)?.into_py(py)));
        }
        let references_dict = references.get(&module_name_str);
        let named_as_str = named_as.to_owned();
        let val = match references_dict.get(&named_as_str) {
            Some(val) => val.clone(),
            None => return Python::with_gil(|py| Ok(PySet::empty(py)?.into_py(py))),
        };

        Python::with_gil(|py| {
            let ret_set = PySet::new(py, &vec![val.into_py(py)])?;
            return Ok(ret_set.into_py(py));
        })
    }

    #[staticmethod]
    pub fn get_reverse_references(module_name: &str, original_name: &str) -> PyResult<PyObject> {
        // reproducing existing bug where name isn't split
        let components = vec![original_name];
        // let components: Vec<&str> = original_name.split('.').collect();
        let base_name = components[0];
        let right_side = if components.len() > 1 {
            components[1..].join(".")
        } else {
            "".to_owned()
        };

        let reverse_references = &get_instance().reverse_references;

        let module_name_str = module_name.to_owned();
        if !reverse_references.contains_key(&module_name_str) {
            return Python::with_gil(|py| Ok(PySet::empty(py)?.into_py(py)));
        }
        let reverse_references_dict = reverse_references.get(&module_name_str);

        let base_name_str = base_name.to_owned();
        if !reverse_references_dict.contains_key(&base_name_str) {
            return Python::with_gil(|py| Ok(PySet::empty(py)?.into_py(py)));
        }
        let reverse_references_set = reverse_references_dict.get(&base_name_str);

        return Python::with_gil(|py| {
            let result: Vec<PyObject> = reverse_references_set
                .iter()
                .map(|mod_and_name| {
                    let module = mod_and_name.module.clone();
                    let name = if !right_side.is_empty() {
                        format!("{}.{}", mod_and_name.name.clone(), right_side)
                    } else {
                        mod_and_name.name.clone()
                    };
                    ModAndName { module, name }.into_py(py)
                })
                .collect();
            let ret_set = PySet::new(py, &result)?;
            return Ok(ret_set.into_py(py));
        });
    }

    #[staticmethod]
    fn get_original_name(module_name: &str, named_as: &str) -> PyResult<String> {
        let renames_dict = &get_instance().renames;
        let original_name = match renames_dict.get(&ModAndName {
            module: module_name.to_owned(),
            name: named_as.to_owned(),
        }) {
            Some(original_name) => original_name.clone(),
            None => named_as.to_owned(),
        };

        Ok(original_name)
    }

    #[staticmethod]
    fn _debug_references() -> PyResult<PyObject> {
        let references = &get_instance().references;
        return Python::with_gil(|py| {
            let ret_dict = PyDict::new(py);
            // DefaultHashLib is missing iter()
            for module_name in references.keys() {
                let references_dict = references.get(module_name);
                let module_dict = PyDict::new(py);
                for (named_as, mod_and_name) in references_dict.iter() {
                    module_dict.set_item(named_as, mod_and_name.clone().into_py(py))?;
                }
                ret_dict.set_item(module_name, module_dict)?;
            }
            return Ok(ret_dict.into_py(py));
        });
    }

    #[staticmethod]
    fn _debug_reverse_references() -> PyResult<PyObject> {
        let reverse_references = &get_instance().reverse_references;
        return Python::with_gil(|py| {
            let ret_dict = PyDict::new(py);
            // DefaultHashLib is missing iter()
            for module_name in reverse_references.keys() {
                let reverse_references_dict = reverse_references.get(module_name);
                let module_dict = PyDict::new(py);
                // for (base_name, mod_and_name_set) in reverse_references_dict.iter() {
                for base_name in reverse_references.keys() {
                    let mod_and_name_set = reverse_references_dict.get(base_name);
                    let mod_and_name_vec: Vec<PyObject> = mod_and_name_set
                        .iter()
                        .map(|mod_and_name| mod_and_name.clone().into_py(py))
                        .collect();
                    let mod_and_name_set = PySet::new(py, &mod_and_name_vec)?;
                    module_dict.set_item(base_name, mod_and_name_set)?;
                }
                ret_dict.set_item(module_name, module_dict)?;
            }
            return Ok(ret_dict.into_py(py));
        });
    }

    #[staticmethod]
    fn _debug_renames() -> PyResult<PyObject> {
        let renames = &get_instance().renames;
        return Python::with_gil(|py| {
            let ret_dict = PyDict::new(py);
            // DefaultHashLib is missing iter()
            for mod_and_name in renames.keys() {
                let original_name = renames.get(mod_and_name);
                ret_dict.set_item(
                    mod_and_name.clone().into_py(py),
                    original_name.clone().into_py(py),
                )?;
            }
            return Ok(ret_dict.into_py(py));
        });
    }
}

#[pymodule]
fn _megamock(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<References>()?;
    Ok(())
}
