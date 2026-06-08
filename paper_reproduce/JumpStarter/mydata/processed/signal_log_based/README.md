# signal_log_based

This tuning dataset drops all `_latency` columns and keeps:

- cpu
- mem
- request_rate
- error_rate

It creates two combined test sets:

- `test_all_signal`: includes all faults.
- `test_no_delay_signal`: excludes `fault_delay_cart_repeat_500ms`.

Run from `detector/`:

```powershell
$env:PYTHONNOUSERSITE='1'
conda run -n jumpstarter python run_detector.py -c ..\mydata\processed\signal_log_based\configs\test_all_signal.yml
conda run -n jumpstarter python run_detector.py -c ..\mydata\processed\signal_log_based\configs\test_no_delay_signal.yml
```
