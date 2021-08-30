"""
utilities to load runs
"""
from typing import Union
import pprint
from qcodes.dataset.dataset import load_by_run_spec, load_by_guid
from qcodes.dataset.guids import validate_guid_format


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


def list_parameters(id: Union[int, str]):
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

    pp = pprint.PrettyPrinter(indent=2, sort_dicts=False)
    pp.pprint(output)
