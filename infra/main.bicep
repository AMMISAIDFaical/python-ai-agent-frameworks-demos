targetScope = 'resourceGroup'

@minLength(1)
@maxLength(64)
param environmentName string

@minLength(1)
@allowed([
  'francecentral'
  'westeurope'
  'uksouth'
  'switzerlandnorth'
])
@metadata({
  azd: {
    type: 'location'
  }
})
param location string

var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var prefix = '${environmentName}${resourceToken}'
var tags = {
  'azd-env-name': environmentName
  'project': 'student-budget-search'
  'owner': 'yourname'
}

var searchServiceName = '${prefix}-search'

resource searchService 'Microsoft.Search/searchServices@2023-11-01' = {
  name: searchServiceName
  location: location
  tags: tags
  sku: {
    name: 'basic' // cheaper than 'standard'
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
  }
}

output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_RESOURCE_GROUP string = resourceGroup().name
output AZURE_SEARCH_SERVICE string = searchService.name
output AZURE_SEARCH_ENDPOINT string = 'https://${searchService.name}.search.windows.net'
