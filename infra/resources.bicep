targetScope = 'resourceGroup'

param environmentName string
param location string
param principalId string
param allowedIpCidr string
param webExists bool
param modelName string
param modelVersion string
param modelSkuName string
param modelCapacity int

var token = toLower(uniqueString(subscription().subscriptionId, environmentName, location))
var foundryName = take('fdt-${token}', 64)
var projectName = 'financial-twins'
var storageName = take('fdt${token}', 24)
var cosmosName = take('fdt-cosmos-${token}', 44)
var registryName = take('fdt${token}acr', 50)
var containerEnvironmentName = take('cae-${environmentName}', 60)
var webName = take('ca-${environmentName}', 32)
var pipelineJobName = take('job-${environmentName}-profiles', 32)
var simulationJobName = take('job-${environmentName}-foundry', 32)
var databaseName = 'financial-twins'
var modelDeploymentName = 'chat'

var foundryUserRoleId = '53ca6127-db72-4b80-b1b0-d745d6d5456d'
var foundryProjectManagerRoleId = 'eadc314b-1a2d-4efa-be10-5d325db5065e'
var foundryAgentConsumerRoleId = 'eed3b665-ab3a-47b6-8f48-c9382fb1dad6'
var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
var acrPushRoleId = '8311e382-0749-4cb8-b61a-304f252e45ec'
var blobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var cosmosDataContributorRoleId = '00000000-0000-0000-0000-000000000002'

var commonTags = {
  environment: environmentName
  'azd-env-name': environmentName
  workload: 'foundry-financial-digital-twins'
  dataClassification: 'synthetic-only'
}

resource logs 'Microsoft.OperationalInsights/workspaces@2026-03-01' = {
  name: take('log-${environmentName}-${token}', 63)
  location: location
  tags: commonTags
  properties: {
    retentionInDays: 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    sku: {
      name: 'PerGB2018'
    }
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: take('appi-${environmentName}-${token}', 255)
  location: location
  kind: 'web'
  tags: commonTags
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logs.id
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

resource foundry 'Microsoft.CognitiveServices/accounts@2026-09-01' = {
  name: foundryName
  location: location
  kind: 'AIServices'
  tags: commonTags
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'S0'
  }
  properties: {
    allowProjectManagement: true
    customSubDomainName: foundryName
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
    restrictOutboundNetworkAccess: false
  }
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2026-09-01' = {
  parent: foundry
  name: projectName
  location: location
  tags: commonTags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    displayName: 'Financial Digital Twins'
    description: 'Synthetic Agro product scenario laboratory'
  }
}

resource model 'Microsoft.CognitiveServices/accounts/deployments@2026-09-01' = {
  parent: foundry
  name: modelDeploymentName
  sku: {
    name: modelSkuName
    capacity: modelCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: modelName
      version: modelVersion
    }
    versionUpgradeOption: 'NoAutoUpgrade'
  }
}

resource projectFoundryAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundry.id, project.id, foundryUserRoleId)
  scope: foundry
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      foundryUserRoleId
    )
  }
}

resource deployerProjectAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(project.id, principalId, foundryProjectManagerRoleId)
  scope: project
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      foundryProjectManagerRoleId
    )
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2026-09-01' = {
  name: storageName
  location: location
  tags: commonTags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
    isHnsEnabled: true
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: 'Enabled'
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2026-09-01' = {
  parent: storage
  name: 'default'
}

resource rawEvents 'Microsoft.Storage/storageAccounts/blobServices/containers@2026-09-01' = {
  parent: blobService
  name: 'raw-events'
  properties: {
    publicAccess: 'None'
  }
}

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2026-03-15' = {
  name: cosmosName
  location: location
  tags: commonTags
  kind: 'GlobalDocumentDB'
  properties: {
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    databaseAccountOfferType: 'Standard'
    disableKeyBasedMetadataWriteAccess: true
    disableLocalAuth: true
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    minimalTlsVersion: 'Tls12'
    publicNetworkAccess: 'Enabled'
  }
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2026-03-15' = {
  parent: cosmos
  name: databaseName
  properties: {
    resource: {
      id: databaseName
    }
  }
}

resource customerTwins 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2026-03-15' = {
  parent: database
  name: 'customerTwins'
  properties: {
    resource: {
      id: 'customerTwins'
      partitionKey: {
        kind: 'Hash'
        paths: [
          '/id'
        ]
      }
    }
  }
}

resource simulationRuns 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2026-03-15' = {
  parent: database
  name: 'simulationRuns'
  properties: {
    resource: {
      id: 'simulationRuns'
      partitionKey: {
        kind: 'Hash'
        paths: [
          '/id'
        ]
      }
    }
  }
}

resource twinDecisions 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2026-03-15' = {
  parent: database
  name: 'twinDecisions'
  properties: {
    resource: {
      id: 'twinDecisions'
      partitionKey: {
        kind: 'Hash'
        paths: [
          '/twin_id'
        ]
      }
    }
  }
}

resource registry 'Microsoft.ContainerRegistry/registries@2025-11-01' = {
  name: registryName
  location: location
  tags: commonTags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
    anonymousPullEnabled: false
    dataEndpointEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

resource deployerRegistryPush 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, principalId, acrPushRoleId)
  scope: registry
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      acrPushRoleId
    )
  }
}

resource containerEnvironment 'Microsoft.App/managedEnvironments@2026-01-01' = {
  name: containerEnvironmentName
  location: location
  tags: commonTags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
  }
}

var applicationEnvironment = [
  {
    name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
    value: appInsights.properties.ConnectionString
  }
  {
    name: 'FOUNDRY_PROJECT_ENDPOINT'
    value: 'https://${foundryName}.services.ai.azure.com/api/projects/${projectName}'
  }
  {
    name: 'AZURE_AI_MODEL_DEPLOYMENT_NAME'
    value: modelDeploymentName
  }
  {
    name: 'FOUNDRY_CUSTOMER_TWIN_AGENT'
    value: 'customer-twin'
  }
  {
    name: 'COSMOS_ENDPOINT'
    value: cosmos.properties.documentEndpoint
  }
  {
    name: 'COSMOS_DATABASE'
    value: databaseName
  }
  {
    name: 'STORAGE_ACCOUNT_URL'
    value: 'https://${storage.name}.blob.${environment().suffixes.storage}'
  }
  {
    name: 'RAW_EVENTS_CONTAINER'
    value: rawEvents.name
  }
  {
    name: 'DEFAULT_POPULATION_SIZE'
    value: '120'
  }
  {
    name: 'DEFAULT_POPULATION_SEED'
    value: 'agro-demo-2026'
  }
]

resource existingWeb 'Microsoft.App/containerApps@2026-01-01' existing = if (webExists) {
  name: webName
}

var placeholderImage = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
var activeImage = webExists
  ? existingWeb!.properties.template.containers[0].image
  : placeholderImage

resource web 'Microsoft.App/containerApps@2026-01-01' = {
  name: webName
  location: location
  tags: union(commonTags, {
    'azd-service-name': 'web'
  })
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        allowInsecure: false
        external: true
        ipSecurityRestrictions: [
          {
            action: 'Allow'
            description: 'Validation client'
            ipAddressRange: allowedIpCidr
            name: 'validation-client'
          }
        ]
        targetPort: webExists ? 8000 : 80
        transport: 'auto'
      }
      registries: [
        {
          identity: 'system'
          server: registry.properties.loginServer
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'web'
          image: activeImage
          env: applicationEnvironment
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        maxReplicas: 2
        minReplicas: 0
      }
    }
  }
}

resource pipelineJob 'Microsoft.App/jobs@2026-01-01' = {
  name: pipelineJobName
  location: location
  tags: commonTags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    environmentId: containerEnvironment.id
    configuration: {
      replicaRetryLimit: 0
      replicaTimeout: 900
      triggerType: 'Manual'
      registries: [
        {
          identity: 'system'
          server: registry.properties.loginServer
        }
      ]
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
    }
    template: {
      containers: [
        {
          name: 'profile-pipeline'
          image: activeImage
          command: [
            'sh'
            '-c'
          ]
          args: [
            'python -m financial_twins provision-agents && python -m financial_twins generate --azure --count 120 --seed agro-demo-2026 --output /tmp/output'
          ]
          env: applicationEnvironment
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }

      ]
    }
  }
}

resource simulationJob 'Microsoft.App/jobs@2026-01-01' = {
  name: simulationJobName
  location: location
  tags: commonTags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    environmentId: containerEnvironment.id
    configuration: {
      replicaRetryLimit: 0
      replicaTimeout: 7200
      triggerType: 'Manual'
      registries: [
        {
          identity: 'system'
          server: registry.properties.loginServer
        }
      ]
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
    }
    template: {
      containers: [
        {
          name: 'foundry-simulation'
          image: activeImage
          command: [
            'python'
          ]
          args: [
            '-m'
            'financial_twins'
            'simulate-foundry'
            '--azure'
            '--count'
            '120'
            '--seed'
            'agro-demo-2026'
            '--output'
            '/tmp/foundry-simulation.json'
          ]
          env: applicationEnvironment
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
    }
  }
}

resource webRegistryPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, web.id, acrPullRoleId)
  scope: registry
  properties: {
    principalId: web.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      acrPullRoleId
    )
  }
}

resource pipelineRegistryPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, pipelineJob.id, acrPullRoleId)
  scope: registry
  properties: {
    principalId: pipelineJob.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      acrPullRoleId
    )
  }

}

resource simulationRegistryPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, simulationJob.id, acrPullRoleId)
  scope: registry
  properties: {
    principalId: simulationJob.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      acrPullRoleId
    )
  }
}

resource webFoundryAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(project.id, web.id, foundryAgentConsumerRoleId)
  scope: project
  properties: {
    principalId: web.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      foundryAgentConsumerRoleId
    )
  }
}

resource pipelineFoundryAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundry.id, pipelineJob.id, foundryUserRoleId)
  scope: foundry
  properties: {
    principalId: pipelineJob.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      foundryUserRoleId
    )
  }

}

resource simulationFoundryAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(project.id, simulationJob.id, foundryAgentConsumerRoleId)
  scope: project
  properties: {
    principalId: simulationJob.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      foundryAgentConsumerRoleId
    )
  }
}

resource webStorageAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, web.id, blobDataContributorRoleId)
  scope: storage
  properties: {
    principalId: web.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      blobDataContributorRoleId
    )
  }
}

resource pipelineStorageAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, pipelineJob.id, blobDataContributorRoleId)
  scope: storage
  properties: {
    principalId: pipelineJob.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      blobDataContributorRoleId
    )
  }

}

resource simulationStorageAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, simulationJob.id, blobDataContributorRoleId)
  scope: storage
  properties: {
    principalId: simulationJob.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      blobDataContributorRoleId
    )
  }
}

resource webCosmosAccess 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2026-03-15' = {
  parent: cosmos
  name: guid(cosmos.id, web.id, cosmosDataContributorRoleId)
  properties: {
    principalId: web.identity.principalId
    roleDefinitionId: '${cosmos.id}/sqlRoleDefinitions/${cosmosDataContributorRoleId}'
    scope: cosmos.id
  }
}

resource pipelineCosmosAccess 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2026-03-15' = {
  parent: cosmos
  name: guid(cosmos.id, pipelineJob.id, cosmosDataContributorRoleId)
  properties: {
    principalId: pipelineJob.identity.principalId
    roleDefinitionId: '${cosmos.id}/sqlRoleDefinitions/${cosmosDataContributorRoleId}'
    scope: cosmos.id
  }

}

resource simulationCosmosAccess 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2026-03-15' = {
  parent: cosmos
  name: guid(cosmos.id, simulationJob.id, cosmosDataContributorRoleId)
  properties: {
    principalId: simulationJob.identity.principalId
    roleDefinitionId: '${cosmos.id}/sqlRoleDefinitions/${cosmosDataContributorRoleId}'
    scope: cosmos.id
  }
}

output SERVICE_WEB_RESOURCE_NAME string = web.name
output SERVICE_WEB_ENDPOINT string = 'https://${web.properties.configuration.ingress.fqdn}'
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = registry.properties.loginServer
output PIPELINE_JOB_NAME string = pipelineJob.name
output FOUNDRY_BATCH_JOB_NAME string = simulationJob.name
output FOUNDRY_PROJECT_ENDPOINT string = 'https://${foundryName}.services.ai.azure.com/api/projects/${projectName}'
output AZURE_AI_MODEL_DEPLOYMENT_NAME string = model.name
