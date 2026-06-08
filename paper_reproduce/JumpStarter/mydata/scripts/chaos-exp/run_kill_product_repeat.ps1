$preSeconds = 10 * 60
$recoverSeconds = 5 * 60
$cycles = 3
$logFile = ".\chaos-exp\kill_product_repeat_log.txt"
$chaosName = "kill-product-repeat"
$yamlFile = ".\chaos-exp\kill-product-repeat.yaml"

"Experiment: repeated productcatalogservice pod kill" | Tee-Object -FilePath $logFile
"Script start: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Tee-Object -FilePath $logFile -Append
"Pre-normal seconds: $preSeconds" | Tee-Object -FilePath $logFile -Append
"Recover seconds between cycles: $recoverSeconds" | Tee-Object -FilePath $logFile -Append
"Cycles: $cycles" | Tee-Object -FilePath $logFile -Append

Write-Host "Clean old PodChaos if exists..."
kubectl delete podchaos $chaosName -n chaos-mesh --ignore-not-found

Write-Host "Waiting before first pod kill..."
Start-Sleep -Seconds $preSeconds

for ($i = 1; $i -le $cycles; $i++) {
    Write-Host ""
    Write-Host "================ Cycle $i ================"

    # 1. 确保上一轮对象已经不存在
    Write-Host "Ensure no old PodChaos exists..."
    kubectl delete podchaos $chaosName -n chaos-mesh --ignore-not-found

    while ($true) {
        $existing = kubectl get podchaos $chaosName -n chaos-mesh --ignore-not-found
        if ([string]::IsNullOrWhiteSpace($existing)) {
            break
        }
        Write-Host "PodChaos still exists, waiting..."
        Start-Sleep -Seconds 3
    }

    # 2. 记录 kill 时间并创建 PodChaos
    $killTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "cycle_${i}_kill_time: $killTime" | Tee-Object -FilePath $logFile -Append
    Write-Host "Cycle $i pod kill time: $killTime"

    kubectl apply -f $yamlFile

    # 3. 给 Chaos Mesh 一点时间触发 kill
    Start-Sleep -Seconds 20

    # 4. 删除 PodChaos 对象
    Write-Host "Delete PodChaos object..."
    kubectl delete podchaos $chaosName -n chaos-mesh --ignore-not-found

    # 5. 等 PodChaos 真正消失
    while ($true) {
        $existing = kubectl get podchaos $chaosName -n chaos-mesh --ignore-not-found
        if ([string]::IsNullOrWhiteSpace($existing)) {
            Write-Host "PodChaos deleted."
            break
        }
        Write-Host "PodChaos still exists after delete, waiting..."
        Start-Sleep -Seconds 3
    }

    # 6. 等 productcatalogservice 重新 Ready
    Write-Host "Waiting for productcatalogservice pod to become Ready..."
    kubectl wait --for=condition=Ready pod -n onlineboutique -l app=productcatalogservice --timeout=180s

    Write-Host "Current productcatalogservice pod status:"
    kubectl get pods -n onlineboutique | findstr productcatalogservice

    if ($i -lt $cycles) {
        Write-Host "Recovery gap before next cycle..."
        Start-Sleep -Seconds $recoverSeconds
    }
}

"Script end: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Tee-Object -FilePath $logFile -Append
Write-Host "Repeated pod kill experiment finished."
Write-Host "Log saved to $logFile"