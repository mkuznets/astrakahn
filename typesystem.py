#!/usr/bin/env python3

def cast_message(data_type, data):
    """
    Casts the content of an AstraKahn message to the given type.  If the
    content cannot be matched by the type, an exception is raised.

    Args:
        data_type: A matching datatype in the form of AstraKahn CAL term
            algebra.  In terms of Python it has the same structure as a
            data, except for the primitive elements, that can either be
            `int` or `float` classes, and `wildcards':
                * ``object`` class as the last element of a list
                * ``__rest__': object`` element of a dict
            that functions like instantiated variables in term algebra.
        data: A content of AstraKahn message that can be a primitive
            (int or float), tuple, list, or dictionary (i.e. a record in
            terms of AstraKahn CAL).  Compound types can have a nested
            structure (e.g. it's possible to have a list of tuples).

    Returns:
        The result of matching i.e. either the original data unaltered or
        fitted accoring to the type.
    """

    is_primitive = lambda m: (m == int or m == float)
    is_compound = lambda m: (type(m) == list
                             or type(m) == tuple
                             or type(m) == dict)
    get_type = lambda m: m if is_primitive(m) else type(m)

    # Primitive types are passed as is (provided that the type is correct)
    if is_primitive(data_type):
        assert isinstance(data, data_type), \
            "Type of the message doesn't match"
        return data

    # Check compound types for correspondence.
    assert type(data) == type(data_type), \
        "Type of the message doesn't match"

    # Tuple
    if type(data_type) == tuple:
        assert len(data_type) == len(data), \
            "Lenght of the tuple doesn't match"

        for i in range(len(data_type)):
            if not is_primitive(data_type[i]):
                data = data[:i] \
                        + (cast_message(data_type[i], data[i]),) \
                        + data[i+1:]
            assert isinstance(data[i], get_type(data_type[i])), \
                "Type of the elements doesn't match"
        return data

    # List
    elif type(data_type) == list:

        # A list-term match a longer list with possible loss of data
        if len(data_type) < len(data) \
                or (len(data_type) == len(data)
                    and data_type[-1] == object):
            out_list = []

            # Wildcard in the end of list-term match the tail of the list
            # IMPORTANT: The assumption is made that there can be only
            # one wildcard
            if data_type[-1] == object:
                out_list.append(data[len(data_type)-1:])
                # Remove wildcard from the passport
                data_type.pop()
                data = data[:len(data_type)]

            for i in range(len(data_type)):
                if not is_primitive(data_type[i]):
                    data[i] = cast_message(data_type[i], data[i])
                assert isinstance(data[i], get_type(data_type[i])), \
                    "Type of the elements doesn't match"

            # Add corresponding part of the input list
            out_list = data[:len(data_type)] + out_list

            return out_list

        # Direct correspondence of lists: check types and pass through
        elif len(data_type) == len(data):
            for i in range(len(data_type)):
                if not is_primitive(data_type[i]):
                    data[i] = cast_message(data_type[i], data[i])
                assert isinstance(data[i], get_type(data_type[i])), \
                    "Type of the elements doesn't match"
            return data

        assert False, "Input list can't be shorter than required list-term"

    # Record
    elif type(data_type) == dict:

        common_labels = set(data_type.keys()) & set(data.keys())
        rest_labels = data.keys() - common_labels

        for l in common_labels:
            if not is_primitive(data_type[l]):
                data[l] = cast_message(data_type[l], data[l])
            assert isinstance(data[l], get_type(data_type[l])), \
                "Type of the elements doesn't match"

        out_dict = {l: data[l] for l in common_labels}

        # If the passport contains a wildcard, add a special element
        # labeled '__rest__' with the reminder of the dictionary.
        if '__rest__' in data_type \
                and data_type['__rest__'] == object:
            out_dict['__rest__'] = {l: data[l] for l in rest_labels}

        return out_dict


if __name__ == '__main__':
    passport = {'a': (int, [{'m': float}, int]), '__rest__': object}
    print(cast_message(passport, {'a': (5, [{'m': 4.}, 5, 4]), 'b': 3.}))
