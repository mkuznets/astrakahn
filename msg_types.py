#!/usr/bin/env python3


class Msg:

    def unpack_message(input_passport, msg):
        """
        Unpack message and perform some trivial checks according to
        box passport
        """

        is_elementary = lambda m: (m == int or m == float)
        is_compound = lambda m: (type(m) == list
                                 or type(m) == tuple
                                 or type(m) == dict)
        get_type = lambda m: m if is_elementary(m) else type(m)

        # Primitive types are passed as-is
        if is_elementary(input_passport):
            assert isinstance(msg, input_passport), \
                "Type of the message doesn't match"
            return msg

        # Check compound types for correspondence
        assert type(msg) == type(input_passport), \
            "Type of the message doesn't match"

        # Tuple
        if type(input_passport) == tuple:
            assert len(input_passport) == len(msg), \
                "Lenght of the tuple doesn't match"

            for i in range(len(input_passport)):
                assert isinstance(msg[i], get_type(input_passport[i])), \
                    "Type of the elements doesn't match"
            return msg

        # List
        elif type(input_passport) == list:

            # A list-term match a longer list with possible loss of data
            if len(input_passport) < len(msg) \
                    or (len(input_passport) == len(msg)
                        and input_passport[-1] == object):
                out_list = []

                # Wildcard in the end of list-term match the tail of the list
                # IMPORTANT: The assumption is made that there can be only
                # one wildcard
                if input_passport[-1] == object:
                    out_list.append(msg[len(input_passport)-1:])
                    # Remove wildcard from the passport
                    input_passport.pop()
                    msg = msg[:len(input_passport)]

                for i in range(len(input_passport)):
                    assert isinstance(msg[i], get_type(input_passport[i])), \
                        "Type of the elements doesn't match"

                # Add corresponding part of the input list
                out_list = msg[:len(input_passport)] + out_list

                return out_list

            # Direct correspondence of lists: check types and pass through
            elif len(input_passport) == len(msg):
                for i in range(len(input_passport)):
                    assert isinstance(msg[i], get_type(input_passport[i])), \
                        "Type of the elements doesn't match"
                return msg

            assert False, "Input list can't be shorter than required list-term"

        # Record
        elif type(input_passport) == dict:

            common_labels = set(input_passport.keys()) & set(msg.keys())
            rest_labels = msg.keys() - common_labels

            for l in common_labels:
                assert type(msg[l]) == input_passport[l], \
                    "Type of the elements doesn't match"

            out_dict = {l: msg[l] for l in common_labels}

            # If the passport contains a wildcard, add a special element
            # labeled '__rest__' with the reminder of the dictionary.
            if '__rest__' in input_passport \
                    and input_passport['__rest__'] == object:
                out_dict['__rest__'] = {l: msg[l] for l in rest_labels}

            return out_dict
