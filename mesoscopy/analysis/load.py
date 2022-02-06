"""
utilities to load runs
"""
from typing import Union, Optional, List
import pprint
import qcodes as qc
from qcodes.dataset.data_set import load_by_run_spec, load_by_guid, DataSet
from qcodes.dataset.guids import validate_guid_format
from qcodes.dataset.data_export import (
    DSPlotData, DataSetProtocol, _get_data_from_ds)
from qcodes.dataset.sqlite.connection import transaction
from qcodes.dataset.sqlite.query_helpers import one


def get_dataset(id: Union[int, str]):
    """
    returns dataset for a given id, that can be run_id or guid
    """

    if isinstance(id, int):
        dataset = load_by_run_spec(captured_run_id=id)
    elif isinstance(id, str):
        validate_guid_format(id)
        dataset = load_by_guid(id)

    return dataset


def list_parameters(id: Union[int, str],
                    print: Optional[bool] = True,
                    out: Optional[bool] = False):
    """
    list all parameters for a given dataset
    """
    dataset = get_dataset(id)
    output = {
        'dependent': [],
        'independent': [],
    }

    for paramspecs in dataset.paramspecs.values():
        if not paramspecs.depends_on:
            output['independent'].append(paramspecs.name)
        else:
            output['dependent'].append(paramspecs.name)

    if print:
        pp = pprint.PrettyPrinter(indent=2, sort_dicts=False)
        pp.pprint(output)

    if out:
        return output


def get_data_by_paramname(ds: DataSetProtocol,
                          param_name: str) -> List[DSPlotData]:
    try:
        dataset = _get_data_from_ds(ds)

        for i in range(len(dataset)):
            if dataset[i][2]['name'] == param_name:
                return dataset[i]

    except ValueError:
        # data = ds.get_parameter_data()[param_name]
        # keys = list(data.keys())
        # return [data[keys[1],keys[2],keys[0]]
        print('data not complete')


def get_run_timestamp(id):
    database = qc.config['core']['db_location']

    ds = DataSet(database)
    sql = """
    SELECT run_timestamp
    FROM
      runs
    WHERE
      run_id=?
    """
    transac = transaction(ds.conn, sql, id)
    run_ts = one(transac, 'run_timestamp')
    return run_ts


def import_sweep(num):
    ds = get_dataset(num)
    dependent = {}
    independent = {}

    for paramspecs in ds.paramspecs.values():
        if paramspecs.depends_on:
            name_dep = paramspecs.name
            dependent[name_dep] = ds.get_parameter_data()[name_dep][name_dep]
        else:
            pass # indep parameters come first in the list
    for paramspecs in ds.paramspecs.values():
        if not paramspecs.depends_on:
            name_ind = paramspecs.name
            independent[name_ind] = ds.get_parameter_data()[name_dep][name_ind]

    return independent, dependent

# TODO: make functions to import only selected parameters.
