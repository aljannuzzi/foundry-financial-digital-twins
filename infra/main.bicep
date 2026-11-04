targetScope = 'subscription'

@minLength(3)
@maxLength(24)
param environmentName string

param location string = 'eastus2'
param principalId string
param allowedIpCidr string
param webExists bool = false
param modelName string = 'gpt-5.4-mini'
param modelVersion string = '2026-03-17'
param modelSkuName string = 'GlobalStandard'
param modelCapacity int = 10

var resourceGroupName = 'rg-${environmentName}'

resource resourceGroup 'Microsoft.Resources/resourceGroups@2024-11-01' = {
  name: resourceGroupName
  location: location
  tags: {
    environment: environmentName
    workload: 'foundry-financial-digital-twins'
    dataClassification: 'synthetic-only'
  }
}

module resources './resources.bicep' = {
  name: 'financial-twins-${environmentName}'
  scope: resourceGroup
  params: {
    environmentName: environmentName
    location: location
    principalId: principalId
    allowedIpCidr: allowedIpCidr
    webExists: webExists
    modelName: modelName
    modelVersion: modelVersion
    modelSkuName: modelSkuName
    modelCapacity: modelCapacity
  }
}

output AZURE_RESOURCE_GROUP string = resourceGroup.name
output AZURE_LOCATION string = location
output SERVICE_WEB_RESOURCE_NAME string = resources.outputs.SERVICE_WEB_RESOURCE_NAME
output SERVICE_WEB_ENDPOINT string = resources.outputs.SERVICE_WEB_ENDPOINT
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = resources.outputs.AZURE_CONTAINER_REGISTRY_ENDPOINT
output PIPELINE_JOB_NAME string = resources.outputs.PIPELINE_JOB_NAME
output FOUNDRY_BATCH_JOB_NAME string = resources.outputs.FOUNDRY_BATCH_JOB_NAME
output FOUNDRY_PROJECT_ENDPOINT string = resources.outputs.FOUNDRY_PROJECT_ENDPOINT
output AZURE_AI_MODEL_DEPLOYMENT_NAME string = resources.outputs.AZURE_AI_MODEL_DEPLOYMENT_NAME
