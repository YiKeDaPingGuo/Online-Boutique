$preSeconds = 10 * 60
$faultSeconds = 2 * 60
$recoverSeconds = 5 * 60
$cycles = 3
$logFile = ".\chaos-exp\delay_cart_repeat_log.txt"

"Experiment: repeated cartservice network delay" | Tee-Object -FilePath $logFile
"Script start: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Tee-Object -FilePath $logFile -Append
"Pre-normal seconds: $preSeconds" | Tee-Object -FilePath $logFile -Append
"Fault seconds each cycle: $faultSeconds" | Tee-Object -FilePath $logFile -Append
"Recover seconds between cycles: $recoverSeconds" | Tee-Object -FilePath $logFile -Append
"Cycles: $cycles" | Tee-Object -FilePath $logFile -Append

Write-Host "Waiting before first fault..."
Start-Sleep -Seconds $preSeconds

for ($i = 1; $i -le $cycles; $i++) {
    $faultStart = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "cycle_${i}_fault_start: $faultStart" | Tee-Object -FilePath $logFile -Append

    Write-Host "Cycle $i fault start: $faultStart"
    kubectl apply -f .\chaos-exp\delay-cart-repeat.yaml

    Start-Sleep -Seconds $faultSeconds

    $faultEnd = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "cycle_${i}_fault_end: $faultEnd" | Tee-Object -FilePath $logFile -Append

    Write-Host "Cycle $i fault end: $faultEnd"
    kubectl delete -f .\chaos-exp\delay-cart-repeat.yaml --ignore-not-found

    Start-Sleep -Seconds 10
    kubectl get networkchaos -n chaos-mesh

    if ($i -lt $cycles) {
        Write-Host "Recovery gap before next cycle..."
        Start-Sleep -Seconds $recoverSeconds
    }
}

"Script end: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Tee-Object -FilePath $logFile -Append
Write-Host "Repeated delay experiment finished."
Write-Host "Log saved to $logFile"