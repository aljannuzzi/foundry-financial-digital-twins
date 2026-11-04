$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

$subscription = azd env get-value AZURE_SUBSCRIPTION_ID
$resourceGroup = azd env get-value AZURE_RESOURCE_GROUP
$webName = azd env get-value SERVICE_WEB_RESOURCE_NAME
$jobName = azd env get-value PIPELINE_JOB_NAME
$batchJobName = azd env get-value FOUNDRY_BATCH_JOB_NAME

$image = az containerapp show `
    --subscription $subscription `
    --resource-group $resourceGroup `
    --name $webName `
    --query 'properties.template.containers[0].image' `
    --output tsv
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($image)) {
    throw 'The deployed web image could not be resolved.'
}

az containerapp ingress update `
    --subscription $subscription `
    --resource-group $resourceGroup `
    --name $webName `
    --target-port 8000 `
    --output none
if ($LASTEXITCODE -ne 0) {
    throw 'The web ingress target port could not be updated.'
}

az containerapp job update `
    --subscription $subscription `
    --resource-group $resourceGroup `
    --name $jobName `
    --image $image `
    --output none
if ($LASTEXITCODE -ne 0) {
    throw 'The profile pipeline image could not be updated.'
}

az containerapp job update `
    --subscription $subscription `
    --resource-group $resourceGroup `
    --name $batchJobName `
    --image $image `
    --output none
if ($LASTEXITCODE -ne 0) {
    throw 'The Foundry batch image could not be updated.'
}

$executionName = az containerapp job start `
    --subscription $subscription `
    --resource-group $resourceGroup `
    --name $jobName `
    --query name `
    --output tsv
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($executionName)) {
    throw 'The profile pipeline could not be started.'
}

$deadline = (Get-Date).AddMinutes(20)
do {
    Start-Sleep -Seconds 10
    $status = az containerapp job execution show `
        --subscription $subscription `
        --resource-group $resourceGroup `
        --name $jobName `
        --job-execution-name $executionName `
        --query 'properties.status' `
        --output tsv
    if ($LASTEXITCODE -ne 0) {
        throw 'The profile pipeline execution status could not be read.'
    }
    if ($status -eq 'Succeeded') {
        Write-Host "Profile pipeline $executionName succeeded with image $image"
        exit 0
    }
    if ($status -in @('Failed', 'Stopped', 'Degraded')) {
        throw "Profile pipeline $executionName finished with status $status."
    }
} while ((Get-Date) -lt $deadline)

az containerapp job stop `
    --subscription $subscription `
    --resource-group $resourceGroup `
    --name $jobName `
    --job-execution-name $executionName `
    --output none
if ($LASTEXITCODE -ne 0) {
    throw "Profile pipeline $executionName timed out and could not be stopped."
}
throw "Profile pipeline $executionName did not finish within 20 minutes and was stopped."
