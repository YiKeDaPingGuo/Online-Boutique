$preSeconds = 20 * 60
$faultSeconds = 10 * 60

Write-Host "Experiment: recommendationservice memory stress"
Write-Host "Wait before fault: $preSeconds seconds"
Write-Host "Fault duration: $faultSeconds seconds"

$scriptStart = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "Script start time: $scriptStart"
Write-Host "Waiting before injecting fault..."

Start-Sleep -Seconds $preSeconds

$faultStart = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "Fault start: $faultStart"
kubectl apply -f .\chaos-exp\mem-recommendation.yaml

Start-Sleep -Seconds $faultSeconds

$faultEnd = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "Fault end: $faultEnd"
kubectl delete -f .\chaos-exp\mem-recommendation.yaml --ignore-not-found

Write-Host "Fault deleted. Keep collector running for recovery period."
Write-Host "Record this:"
Write-Host "fault_start: $faultStart"
Write-Host "fault_end: $faultEnd"