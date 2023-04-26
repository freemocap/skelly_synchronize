import logging
from typing import Any, List


def check_list_values_are_equal(input_list: List[Any]) -> Any:
    """Check if values in list are all equal, throw an exception if not (or if list is empty)."""
    unique_values = set(input_list)

    if len(unique_values) == 0:
        raise Exception("list empty")

    if len(unique_values) == 1:
        unique_value = unique_values.pop()
        logging.debug(f"all values in list are equal to {unique_value}")
        return unique_value
    else:
        raise Exception(f"list values are not equal, list is {input_list}")
