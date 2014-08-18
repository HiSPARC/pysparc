"""Classes related to storage of events."""


import tables


class HisparcEvent(tables.IsDescription):
    event_id = tables.UInt32Col(pos=0)
    timestamp = tables.Time32Col(pos=1)
    nanoseconds = tables.UInt32Col(pos=2)
    ext_timestamp = tables.UInt64Col(pos=3)
    data_reduction = tables.BoolCol(pos=4)
    trigger_pattern = tables.UInt32Col(pos=5)
    baseline = tables.Int16Col(shape=4, dflt=-1, pos=6)
    std_dev = tables.Int16Col(shape=4, dflt=-1, pos=7)
    n_peaks = tables.Int16Col(shape=4, dflt=-1, pos=8)
    pulseheights = tables.Int16Col(shape=4, dflt=-1, pos=9)
    integrals = tables.Int32Col(shape=4, dflt=-1, pos=10)
    traces = tables.Int32Col(shape=4, dflt=-1, pos=11)
    event_rate = tables.Float32Col(pos=12)
