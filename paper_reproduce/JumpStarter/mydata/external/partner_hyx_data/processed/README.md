# partner_hyx_data processed

This directory converts the partner HYX pickle data into JumpStarter CSV inputs.

Generated datasets:

- `test_only_full`: original 156 dimensions, test only.
- `train_plus_test_full`: normal train prepended to test, 156 dimensions.
- `test_only_active`: constant dimensions dropped, test only.
- `train_plus_test_active`: constant dimensions dropped, normal train prepended to test.

Window configs are generated for `w5`, `w10`, and `w20`.

Recommended first trial:

```powershell
cd detector
$env:PYTHONNOUSERSITE='1'
conda run -n jumpstarter python run_detector.py -c ..\mydata\external\partner_hyx_data\processed\configs\train_plus_test_active_w10.yml
```
