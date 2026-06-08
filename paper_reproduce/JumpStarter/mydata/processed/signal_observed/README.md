# signal_observed

This directory contains the observed-impact label version of `mydata`.

Compared with `../signal_log_based`, this version keeps the same 44 input
features (`cpu/mem/request_rate/error_rate`) but regenerates labels from
visible metric changes in the CSV files.

Label meaning:

```text
label=1 means the sampling point is inside an observed service-impact window.
```

Recommended config:

```text
configs/test_all_signal_observed_w10.yml
```

The window is 10 sampling points. With a 30-second interval, this is about
5 minutes.
