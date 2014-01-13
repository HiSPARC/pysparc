"""Unassorted utility functions."""


def clipped_map(value, from_low, from_high, to_low, to_high):
    """Clip a value to fit a domain and then map it to a range.

    :param value: value to be clipped and mapped
    :param from_low, from_high: domain of the value.  If the value is
        outside this domain, it will first be clipped.
    :param to_low, to_high: range of the mapped value.  After clipping,
        the value will be mapped to this range.
    :returns: (clipped_value, mapped_value) tuple.

    """
    if value < from_low:
        clipped = from_low
    elif value > from_high:
        clipped = from_high
    else:
        clipped = value

    relative_value = (1. * clipped - from_low) / (from_high - from_low)
    mapped = relative_value * (to_high - to_low) + to_low

    return clipped, mapped


def map_setting(value, value_low, value_high, setting_low, setting_high):
    """Map a value to an integer device setting value.

    When writing settings to a device you usually can only write byte or
    word values, which map to a certain predefined range.  For example,
    when setting a high voltage a domain of 300 V to 1500 V is mapped to a
    byte value in the range of 0x00 to 0xff.  This mapping is not exact.
    This function will perform the mapping and return an integer setting
    value.  This value can then be written to a device.

    :param value: value to be mapped
    :param value_low, value_high: domain of the value.  If the value is
        outside this domain, it will first be clipped.
    :param setting_low, setting_high: range of the mapped value.  After
        clipping, the value will be mapped to this range.
    :returns: setting
    :rtype: int

    """
    clipped_value, mapped_value = clipped_map(value, value_low,
                                              value_high, setting_low,
                                              setting_high)
    setting = int(mapped_value)
    return setting
