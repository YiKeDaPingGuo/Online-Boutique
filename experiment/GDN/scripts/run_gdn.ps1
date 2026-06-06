param(
    [string]$GdnRoot = "D:\soft\AndroidStudioProjects\Online-Boutique\gdn-reproduce",
    [string]$Device = "cpu"
)

Set-Location $GdnRoot

python main.py `
    -dataset onlineboutique `
    -save_path_pattern onlineboutique `
    -slide_win 5 `
    -slide_stride 1 `
    -batch 32 `
    -epoch 30 `
    -dim 64 `
    -topk 15 `
    -out_layer_num 1 `
    -out_layer_inter_dim 64 `
    -val_ratio 0.2 `
    -report val `
    -random_seed 5 `
    -device $Device
