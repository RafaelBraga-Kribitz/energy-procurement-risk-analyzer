// ADR-020 — minimal, free-tier-first Azure footprint for EPRA's publish target.
// Deploy:  az deployment group create -g <rg> -f infra/azure/main.bicep \
//            -p sqlAdminLogin=<login> sqlAdminPassword=<secret> clientIp=<your IP>
// Creates: 1 storage account (Standard_LRS, private container `epra`),
//          1 Azure SQL logical server + 1 serverless DB on the FREE offer
//          (useFreeLimit + AutoPause: the DB pauses instead of billing when the
//          monthly free allowance is used up). No other resources, no secrets in
//          outputs. See docs/AZURE_DEPLOYMENT.md for cost notes.

@description('Short lowercase prefix for resource names (3-11 chars).')
@minLength(3)
@maxLength(11)
param prefix string = 'epra'

@description('Azure region, e.g. westeurope / germanywestcentral / austriaeast.')
param location string = resourceGroup().location

@description('SQL administrator login (stored by you as a GitHub secret, never in the repo).')
param sqlAdminLogin string

@secure()
@description('SQL administrator password.')
param sqlAdminPassword string

@description('Public IP allowed through the SQL firewall (your workstation). Empty = none.')
param clientIp string = ''

@description('Allow Azure services (e.g. GitHub-hosted runners via Azure) through the SQL firewall.')
param allowAzureServices bool = true

var suffix = uniqueString(resourceGroup().id)
var storageName = toLower('${prefix}${take(suffix, 12)}')

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
}

resource container 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'epra'
  properties: { publicAccess: 'None' }
}

resource sqlServer 'Microsoft.Sql/servers@2023-08-01-preview' = {
  name: '${prefix}-sql-${take(suffix, 8)}'
  location: location
  properties: {
    administratorLogin: sqlAdminLogin
    administratorLoginPassword: sqlAdminPassword
    minimalTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
  }
}

resource sqlDb 'Microsoft.Sql/servers/databases@2023-08-01-preview' = {
  parent: sqlServer
  name: 'epra'
  location: location
  sku: { name: 'GP_S_Gen5_2', tier: 'GeneralPurpose' }
  properties: {
    useFreeLimit: true
    freeLimitExhaustionBehavior: 'AutoPause'
    autoPauseDelay: 60
    minCapacity: json('0.5')
    maxSizeBytes: 34359738368
  }
}

resource fwAzure 'Microsoft.Sql/servers/firewallRules@2023-08-01-preview' = if (allowAzureServices) {
  parent: sqlServer
  name: 'AllowAzureServices'
  properties: { startIpAddress: '0.0.0.0', endIpAddress: '0.0.0.0' }
}

resource fwClient 'Microsoft.Sql/servers/firewallRules@2023-08-01-preview' = if (!empty(clientIp)) {
  parent: sqlServer
  name: 'ClientIp'
  properties: { startIpAddress: clientIp, endIpAddress: clientIp }
}

output storageAccountName string = storage.name
output blobEndpoint string = storage.properties.primaryEndpoints.blob
output sqlServerFqdn string = sqlServer.properties.fullyQualifiedDomainName
output sqlDatabaseName string = sqlDb.name
