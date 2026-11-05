targetScope = 'resourceGroup'

param environmentName string
param location string
param principalId string
param allowedIpCidr string
param additionalAllowedIpCidr string
param webExists bool
param webImageName string
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
var registryIdentityName = take('id-${environmentName}-registry', 128)
var webIdentityName = take('id-${environmentName}-web', 128)
var pipelineIdentityName = take('id-${environmentName}-profiles', 128)
var simulationIdentityName = take('id-${environmentName}-foundry', 128)
var virtualNetworkName = take('vnet-${environmentName}', 64)
var infrastructureSubnetName = 'container-apps-infrastructure'
var privateEndpointSubnetName = 'private-endpoints'
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

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2024-07-01' = {
  name: virtualNetworkName
  location: location
  tags: commonTags
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.42.0.0/16'
      ]
    }
  }
}

resource infrastructureSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-07-01' = {
  parent: virtualNetwork
  name: infrastructureSubnetName
  properties: {
    addressPrefix: '10.42.0.0/23'
    delegations: [
      {
        name: 'container-apps'
        properties: {
          serviceName: 'Microsoft.App/environments'
        }
      }
    ]
  }
}

resource privateEndpointSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-07-01' = {
  parent: virtualNetwork
  name: privateEndpointSubnetName
  properties: {
    addressPrefix: '10.42.2.0/24'
    privateEndpointNetworkPolicies: 'Disabled'
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
  dependsOn: [
    model
  ]
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
    publicNetworkAccess: 'Disabled'
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
    publicNetworkAccess: 'Disabled'
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

resource cosmosPrivateDnsZone 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: 'privatelink.documents.azure.com'
  location: 'global'
  tags: commonTags
}

resource cosmosPrivateDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: cosmosPrivateDnsZone
  name: 'cosmos-${environmentName}'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: virtualNetwork.id
    }
  }
}

resource cosmosPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-07-01' = {
  name: take('pe-${cosmosName}', 80)
  location: location
  tags: commonTags
  properties: {
    privateLinkServiceConnections: [
      {
        name: 'cosmos'
        properties: {
          groupIds: [
            'Sql'
          ]
          privateLinkServiceId: cosmos.id
        }
      }
    ]
    subnet: {
      id: privateEndpointSubnet.id
    }
  }
}

resource cosmosPrivateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-07-01' = {
  parent: cosmosPrivateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'cosmos'
        properties: {
          privateDnsZoneId: cosmosPrivateDnsZone.id
        }
      }
    ]
  }
}

resource blobPrivateDnsZone 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: 'privatelink.blob.core.windows.net'
  location: 'global'
  tags: commonTags
}

resource blobPrivateDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: blobPrivateDnsZone
  name: 'blob-${environmentName}'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: virtualNetwork.id
    }
  }
}

resource blobPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-07-01' = {
  name: take('pe-${storageName}-blob', 80)
  location: location
  tags: commonTags
  properties: {
    privateLinkServiceConnections: [
      {
        name: 'blob'
        properties: {
          groupIds: [
            'blob'
          ]
          privateLinkServiceId: storage.id
        }
      }
    ]
    subnet: {
      id: privateEndpointSubnet.id
    }
  }
}

resource blobPrivateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-07-01' = {
  parent: blobPrivateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'blob'
        properties: {
          privateDnsZoneId: blobPrivateDnsZone.id
        }
      }
    ]
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

resource registryIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2024-11-30' = {
  name: registryIdentityName
  location: location
  tags: commonTags
}

resource webIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2024-11-30' = {
  name: webIdentityName
  location: location
  tags: commonTags
}

resource pipelineIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2024-11-30' = {
  name: pipelineIdentityName
  location: location
  tags: commonTags
}

resource simulationIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2024-11-30' = {
  name: simulationIdentityName
  location: location
  tags: commonTags
}

resource registryIdentityPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, registryIdentity.id, acrPullRoleId)
  scope: registry
  properties: {
    principalId: registryIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      acrPullRoleId
    )
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
    vnetConfiguration: {
      infrastructureSubnetId: infrastructureSubnet.id
      internal: false
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
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

var webEnvironment = concat(applicationEnvironment, [
  {
    name: 'AZURE_CLIENT_ID'
    value: webIdentity.properties.clientId
  }
])

var pipelineEnvironment = concat(applicationEnvironment, [
  {
    name: 'AZURE_CLIENT_ID'
    value: pipelineIdentity.properties.clientId
  }
])

var simulationEnvironment = concat(applicationEnvironment, [
  {
    name: 'AZURE_CLIENT_ID'
    value: simulationIdentity.properties.clientId
  }
])

var activeImage = webImageName
var webIpRestrictions = concat([
  {
    action: 'Allow'
    description: 'Primary validation client'
    ipAddressRange: allowedIpCidr
    name: 'validation-client-primary'
  }
], empty(additionalAllowedIpCidr) ? [] : [
  {
    action: 'Allow'
    description: 'Additional validation client'
    ipAddressRange: additionalAllowedIpCidr
    name: 'validation-client-additional'
  }
])

resource web 'Microsoft.App/containerApps@2026-01-01' = {
  name: webName
  location: location
  tags: union(commonTags, {
    'azd-service-name': 'web'
  })
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${registryIdentity.id}': {}
      '${webIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        allowInsecure: false
        external: true
        ipSecurityRestrictions: webIpRestrictions
        targetPort: webExists ? 8000 : 80
        transport: 'auto'
      }
      registries: [
        {
          identity: registryIdentity.id
          server: registry.properties.loginServer
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'web'
          image: activeImage
          env: webEnvironment
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
  dependsOn: [
    registryIdentityPull
  ]
}

resource pipelineJob 'Microsoft.App/jobs@2026-01-01' = {
  name: pipelineJobName
  location: location
  tags: commonTags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${registryIdentity.id}': {}
      '${pipelineIdentity.id}': {}
    }
  }
  properties: {
    environmentId: containerEnvironment.id
    configuration: {
      replicaRetryLimit: 0
      replicaTimeout: 900
      triggerType: 'Manual'
      registries: [
        {
          identity: registryIdentity.id
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
          env: pipelineEnvironment
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }

      ]
    }
  }
  dependsOn: [
    registryIdentityPull
  ]
}

resource simulationJob 'Microsoft.App/jobs@2026-01-01' = {
  name: simulationJobName
  location: location
  tags: commonTags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${registryIdentity.id}': {}
      '${simulationIdentity.id}': {}
    }
  }
  properties: {
    environmentId: containerEnvironment.id
    configuration: {
      replicaRetryLimit: 0
      replicaTimeout: 7200
      triggerType: 'Manual'
      registries: [
        {
          identity: registryIdentity.id
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
            '--concurrency'
            '2'
          ]
          env: simulationEnvironment
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
    }
  }
  dependsOn: [
    registryIdentityPull
  ]
}

resource webFoundryAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(project.id, webIdentity.id, foundryAgentConsumerRoleId)
  scope: project
  properties: {
    principalId: webIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      foundryAgentConsumerRoleId
    )
  }
}

resource pipelineFoundryAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundry.id, pipelineIdentity.id, foundryUserRoleId)
  scope: foundry
  properties: {
    principalId: pipelineIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      foundryUserRoleId
    )
  }

}

resource simulationFoundryAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(project.id, simulationIdentity.id, foundryAgentConsumerRoleId)
  scope: project
  properties: {
    principalId: simulationIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      foundryAgentConsumerRoleId
    )
  }
}

resource webStorageAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, webIdentity.id, blobDataContributorRoleId)
  scope: storage
  properties: {
    principalId: webIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      blobDataContributorRoleId
    )
  }
}

resource pipelineStorageAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, pipelineIdentity.id, blobDataContributorRoleId)
  scope: storage
  properties: {
    principalId: pipelineIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      blobDataContributorRoleId
    )
  }

}

resource simulationStorageAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, simulationIdentity.id, blobDataContributorRoleId)
  scope: storage
  properties: {
    principalId: simulationIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      blobDataContributorRoleId
    )
  }
}

resource webCosmosAccess 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2026-03-15' = {
  parent: cosmos
  name: guid(cosmos.id, webIdentity.id, cosmosDataContributorRoleId)
  properties: {
    principalId: webIdentity.properties.principalId
    roleDefinitionId: '${cosmos.id}/sqlRoleDefinitions/${cosmosDataContributorRoleId}'
    scope: cosmos.id
  }
}

resource pipelineCosmosAccess 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2026-03-15' = {
  parent: cosmos
  name: guid(cosmos.id, pipelineIdentity.id, cosmosDataContributorRoleId)
  properties: {
    principalId: pipelineIdentity.properties.principalId
    roleDefinitionId: '${cosmos.id}/sqlRoleDefinitions/${cosmosDataContributorRoleId}'
    scope: cosmos.id
  }

}

resource simulationCosmosAccess 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2026-03-15' = {
  parent: cosmos
  name: guid(cosmos.id, simulationIdentity.id, cosmosDataContributorRoleId)
  properties: {
    principalId: simulationIdentity.properties.principalId
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
