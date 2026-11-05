$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

$values = @{}
azd env get-values | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        $values[$Matches[1]] = $Matches[2].Trim('"')
    }
}

function Get-EnvironmentValue {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [string]$Default = ''
    )
    if ($values.ContainsKey($Name) -and -not [string]::IsNullOrWhiteSpace($values[$Name])) {
        return $values[$Name]
    }
    return $Default
}

$subscription = Get-EnvironmentValue 'AZURE_SUBSCRIPTION_ID'
$environmentName = Get-EnvironmentValue 'AZURE_ENV_NAME'
$location = Get-EnvironmentValue 'AZURE_LOCATION' 'eastus2'
$modelName = Get-EnvironmentValue 'AZURE_AI_MODEL_NAME' 'gpt-5.4-mini'
$modelVersion = Get-EnvironmentValue 'AZURE_AI_MODEL_VERSION' '2026-03-17'
$modelSku = Get-EnvironmentValue 'AZURE_AI_MODEL_SKU' 'GlobalStandard'
$modelCapacity = [int](Get-EnvironmentValue 'AZURE_AI_MODEL_CAPACITY' '10')

if ([string]::IsNullOrWhiteSpace($subscription)) {
    throw 'AZURE_SUBSCRIPTION_ID is required.'
}
if ([string]::IsNullOrWhiteSpace($environmentName)) {
    throw 'AZURE_ENV_NAME is required.'
}

$requiredProviders = @(
    'Microsoft.App',
    'Microsoft.CognitiveServices',
    'Microsoft.ContainerRegistry',
    'Microsoft.DocumentDB',
    'Microsoft.Insights',
    'Microsoft.ManagedIdentity',
    'Microsoft.Network',
    'Microsoft.OperationalInsights',
    'Microsoft.Storage'
)

foreach ($provider in $requiredProviders) {
    $state = az provider show `
        --subscription $subscription `
        --namespace $provider `
        --query registrationState `
        --output tsv
    if ($LASTEXITCODE -ne 0 -or $state -ne 'Registered') {
        throw "Azure provider $provider is not registered."
    }
}

$models = az cognitiveservices model list `
    --subscription $subscription `
    --location $location `
    --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) {
    throw "Model availability could not be read for $location."
}

$model = $models |
    Where-Object {
        $_.model.name -eq $modelName -and
        $_.model.version -eq $modelVersion
    } |
    Select-Object -First 1
if (-not $model) {
    throw "Model $modelName $modelVersion was not found in $location."
}

$sku = $model.model.skus |
    Where-Object name -eq $modelSku |
    Select-Object -First 1
if (-not $sku) {
    throw "SKU $modelSku is not available for $modelName $modelVersion."
}

$existingCapacity = 0
$resourceGroup = "rg-$environmentName"
$groupExists = az group exists `
    --subscription $subscription `
    --name $resourceGroup
if ($LASTEXITCODE -ne 0) {
    throw "Resource-group state could not be read for $resourceGroup."
}
$webExists = $false
$webImageName = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
if ($groupExists -eq 'true') {
    $managedEnvironments = az containerapp env list `
        --subscription $subscription `
        --resource-group $resourceGroup `
        --output json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) {
        throw 'Existing Container Apps environments could not be read.'
    }
    $existingEnvironment = $managedEnvironments |
        Where-Object { $_.name -eq "cae-$environmentName" } |
        Select-Object -First 1
    if (
        $existingEnvironment -and
        [string]::IsNullOrWhiteSpace(
            $existingEnvironment.properties.vnetConfiguration.infrastructureSubnetId
        )
    ) {
        throw @"
The existing Container Apps environment uses Azure-managed networking and
cannot be upgraded in place to the VNet/private-endpoint topology. This
non-production reference environment must be recreated before continuing.
Run 'azd down --purge', confirm deletion, and then run 'azd up' again.
"@
    }

    $containerApps = az containerapp list `
        --subscription $subscription `
        --resource-group $resourceGroup `
        --output json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) {
        throw 'Existing Container Apps could not be read.'
    }
    $existingWeb = $containerApps |
        Where-Object { $_.tags.'azd-service-name' -eq 'web' } |
        Select-Object -First 1
    $webExists = $null -ne $existingWeb
    if ($webExists) {
        $webImageName = $existingWeb.properties.template.containers[0].image
    }
    $account = az cognitiveservices account list `
        --subscription $subscription `
        --resource-group $resourceGroup `
        --output json | ConvertFrom-Json |
        Where-Object kind -eq 'AIServices' |
        Select-Object -First 1
    if ($account) {
        $deployments = az cognitiveservices account deployment list `
            --subscription $subscription `
            --resource-group $resourceGroup `
            --name $account.name `
            --output json | ConvertFrom-Json
        if ($LASTEXITCODE -ne 0) {
            throw 'Existing model deployments could not be read.'
        }
        $existing = $deployments |
            Where-Object name -eq 'chat' |
            Select-Object -First 1
        if (
            $existing -and
            $existing.properties.model.name -eq $modelName -and
            $existing.properties.model.version -eq $modelVersion -and
            $existing.sku.name -eq $modelSku
        ) {
            $existingCapacity = [int]$existing.sku.capacity
        }
    }
}
azd env set SERVICE_WEB_RESOURCE_EXISTS $webExists.ToString().ToLowerInvariant()
if ($LASTEXITCODE -ne 0) {
    throw 'SERVICE_WEB_RESOURCE_EXISTS could not be updated.'
}
azd env set SERVICE_WEB_IMAGE_NAME $webImageName
if ($LASTEXITCODE -ne 0) {
    throw 'SERVICE_WEB_IMAGE_NAME could not be updated.'
}

$additionalCapacity = [Math]::Max(0, $modelCapacity - $existingCapacity)
$usage = az cognitiveservices usage list `
    --subscription $subscription `
    --location $location `
    --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) {
    throw "Model quota could not be read for $location."
}

$quota = $usage |
    Where-Object { $_.name.value -eq $sku.usageName } |
    Select-Object -First 1
if (-not $quota) {
    throw "Quota $($sku.usageName) was not found in $location."
}
if (($quota.limit - $quota.currentValue) -lt $additionalCapacity) {
    throw "An additional $additionalCapacity capacity units of $($sku.usageName) are required."
}

Write-Host "Azure preflight passed for $modelName $modelVersion ($modelSku) in $location."
