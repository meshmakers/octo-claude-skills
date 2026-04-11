# OctoMesh CLI — Complete Command Reference

All flags use short form with `-` prefix. Required flags are marked with **(R)**.

> **Confirmation prompts:** Destructive commands (Delete, Clean, ClearCache, ResetPassword, RemoveUserFromRole) prompt for confirmation before executing. Add `-y` (`--yes`) to skip the prompt in scripts/CI.

## Context Management

### AddContext
Create or update a named context with service URLs and tenant.
```
octo-cli -c AddContext -n <name> [-isu <identityServicesUri>] [-asu <assetServicesUri>] [-bsu <botServicesUri>] [-csu <communicationServicesUri>] [-rsu <reportingServicesUri>] [-apu <adminPanelUri>] [-tid <tenantId>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-n` | `name` | Name of the context (e.g. `local_meshtest`, `staging_customer1`) | Yes |
| `-isu` | `identityServicesUri` | URI of identity services (e.g. `https://localhost:5003/`) | No |
| `-asu` | `assetServicesUri` | URI of asset repository services (e.g. `https://localhost:5001/`) | No |
| `-bsu` | `botServicesUri` | URI of bot services (e.g. `https://localhost:5009/`) | No |
| `-csu` | `communicationServicesUri` | URI of communication services (e.g. `https://localhost:5015/`) | No |
| `-rsu` | `reportingServicesUri` | URI of reporting services (e.g. `https://localhost:5007/`) | No |
| `-apu` | `adminPanelUri` | URI of admin panel (e.g. `https://localhost:5005/`) | No |
| `-tid` | `tenantId` | ID of tenant (e.g. `meshtest`) | No |

Context naming convention: `{environment}_{tenantId}` (e.g., `local_meshtest`, `staging_meshtest`, `production_customer1`, `test2_v2_meshtest`).

If this is the first context or no active context is set, it is automatically activated. Each context stores its own authentication tokens independently.

### UseContext
Switch the active context or list all available contexts.
```
octo-cli -c UseContext [-n <name>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-n` | `name` | Name of the context to activate | No |

Without `-n`: lists all contexts with their identity URL and tenant ID, marking the active one with `*`.

### RemoveContext
Remove a named context.
```
octo-cli -c RemoveContext -n <name>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-n` | `name` | Name of the context to remove | Yes |

If the removed context was active, another context is automatically promoted.

---

## General

### LogIn
Login to the configured identity services.
```
octo-cli -c LogIn [-i]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-i` | `interactive` | Interactive login by opening a browser for device log-in | No |

### AuthStatus
Gets authentication status. No arguments.
```
octo-cli -c AuthStatus
```

---

## Identity Services

### Setup
Initial identity services setup.
```
octo-cli -c Setup [-e <email>] [-p <password>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-e` | `email` | E-Mail of admin | No |
| `-p` | `password` | Password of admin | No |

### Users

#### GetUsers
Lists all users. No arguments.
```
octo-cli -c GetUsers
```

#### CreateUser
```
octo-cli -c CreateUser -un <userName> -e <eMail> [-p <password>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-un` | `userName` | User name | Yes |
| `-e` | `eMail` | E-Mail of user | Yes |
| `-p` | `password` | Password | No |

#### UpdateUser
```
octo-cli -c UpdateUser -un <userName> [-e <eMail>] [-nun <newUserName>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-un` | `userName` | User name | Yes |
| `-e` | `eMail` | E-Mail of user | No |
| `-nun` | `newUserName` | New user name (if renaming) | No |

#### DeleteUser
```
octo-cli -c DeleteUser -un <userName> [-y]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-un` | `userName` | User name | Yes |
| `-y` | `yes` | Skip confirmation prompt | No |

#### ResetPassword
```
octo-cli -c ResetPassword -un <userName> -p <password> [-y]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-un` | `userName` | User name | Yes |
| `-p` | `password` | New password | Yes |
| `-y` | `yes` | Skip confirmation prompt | No |

#### AddUserToRole
```
octo-cli -c AddUserToRole -un <userName> [-r <role>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-un` | `userName` | User name | Yes |
| `-r` | `role` | Existing role name | No |

#### RemoveUserFromRole
```
octo-cli -c RemoveUserFromRole -un <userName> [-r <role>] [-y]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-un` | `userName` | User name | Yes |
| `-r` | `role` | Role name | No |
| `-y` | `yes` | Skip confirmation prompt | No |

### Roles

#### GetRoles
Lists all roles. No arguments.
```
octo-cli -c GetRoles
```

#### CreateRole
```
octo-cli -c CreateRole -n <name>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-n` | `name` | Name of role | Yes |

#### UpdateRole
```
octo-cli -c UpdateRole -n <name> [-nn <newRoleName>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-n` | `name` | Name of role | Yes |
| `-nn` | `newRoleName` | New name of role | No |

#### DeleteRole
```
octo-cli -c DeleteRole -n <name> [-y]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-n` | `name` | Name of role | Yes |
| `-y` | `yes` | Skip confirmation prompt | No |

### Clients

#### GetClients
Lists all clients. No arguments.
```
octo-cli -c GetClients
```

#### GetClient
```
octo-cli -c GetClient -id <clientId>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-id` | `clientId` | The client ID to retrieve | Yes |

#### AddAuthorizationCodeClient
```
octo-cli -c AddAuthorizationCodeClient -id <clientId> -n <name> -u <clientUri> [-ru <redirectUri>] [-fclo <frontChannelLogoutUri>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-id` | `clientId` | Client ID, must be unique | Yes |
| `-n` | `name` | Display name of client | Yes |
| `-u` | `clientUri` | URI of client | Yes |
| `-ru` | `redirectUri` | Redirect URI for login | No |
| `-fclo` | `frontChannelLogoutUri` | Front-channel logout URI for SLO | No |

#### AddClientCredentialsClient
```
octo-cli -c AddClientCredentialsClient -id <clientId> -n <name> -s <secret>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-id` | `clientId` | Client ID, must be unique | Yes |
| `-n` | `name` | Display name of client | Yes |
| `-s` | `secret` | Secret for client credential auth | Yes |

#### AddDeviceCodeClient
```
octo-cli -c AddDeviceCodeClient -id <clientId> -n <name> -s <secret>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-id` | `clientId` | Client ID, must be unique | Yes |
| `-n` | `name` | Display name of client | Yes |
| `-s` | `secret` | Secret for client credential auth | Yes |

#### UpdateClient
```
octo-cli -c UpdateClient -id <clientId> [-n <name>] [-u <clientUri>] [-ru <redirectUri>] [-fclo <frontChannelLogoutUri>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-id` | `clientId` | Client ID | Yes |
| `-n` | `name` | Display name of client | No |
| `-u` | `clientUri` | URI of client | No |
| `-ru` | `redirectUri` | Redirect URI for login | No |
| `-fclo` | `frontChannelLogoutUri` | Front-channel logout URI for SLO | No |

#### DeleteClient
```
octo-cli -c DeleteClient -id <clientId> [-y]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-id` | `clientId` | Client ID | Yes |
| `-y` | `yes` | Skip confirmation prompt | No |

#### AddScopeToClient
```
octo-cli -c AddScopeToClient -id <clientId> -n <name>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-id` | `clientId` | Client ID | Yes |
| `-n` | `name` | Scope name | Yes |

### Identity Providers

#### GetIdentityProviders
Lists all identity providers. No arguments.
```
octo-cli -c GetIdentityProviders
```

#### AddOAuthIdentityProvider
```
octo-cli -c AddOAuthIdentityProvider -n <name> -e <enabled> -cid <clientId> -cs <clientSecret> -t <type> [-asr <allowSelfRegistration>] [-dgid <defaultGroupRtId>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-n` | `name` | Name of identity provider (unique) | Yes |
| `-e` | `enabled` | `true` or `false` | Yes |
| `-cid` | `clientId` | Client ID from provider | Yes |
| `-cs` | `clientSecret` | Client secret from provider | Yes |
| `-t` | `type` | Provider type: `google`, `microsoft`, `facebook` | Yes |
| `-asr` | `allowSelfRegistration` | Allow self-registration (`true`/`false`) | No |
| `-dgid` | `defaultGroupRtId` | Default group RtId for new users | No |

#### AddOpenLdapIdentityProvider
```
octo-cli -c AddOpenLdapIdentityProvider -n <name> -e <enabled> -h <host> -p <port> -ubdn <userBaseDn> -uan <userAttributeName> [-asr <allowSelfRegistration>] [-dgid <defaultGroupRtId>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-n` | `name` | Name (unique) | Yes |
| `-e` | `enabled` | `true` or `false` | Yes |
| `-h` | `host` | Host | Yes |
| `-p` | `port` | Port | Yes |
| `-ubdn` | `userBaseDn` | User base DN (e.g. `cn=users,dc=meshmakers,dc=cloud`) | Yes |
| `-uan` | `userAttributeName` | User name attribute (e.g. `uid`) | Yes |
| `-asr` | `allowSelfRegistration` | Allow self-registration (`true`/`false`) | No |
| `-dgid` | `defaultGroupRtId` | Default group RtId for new users | No |

#### AddAdIdentityProvider
```
octo-cli -c AddAdIdentityProvider -n <name> -e <enabled> -h <host> -p <port> [-asr <allowSelfRegistration>] [-dgid <defaultGroupRtId>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-n` | `name` | Name (unique) | Yes |
| `-e` | `enabled` | `true` or `false` | Yes |
| `-h` | `host` | Host | Yes |
| `-p` | `port` | Port | Yes |
| `-asr` | `allowSelfRegistration` | Allow self-registration (`true`/`false`) | No |
| `-dgid` | `defaultGroupRtId` | Default group RtId for new users | No |

#### AddAzureEntryIdIdentityProvider
```
octo-cli -c AddAzureEntryIdIdentityProvider -n <name> -t <tenantId> -e <enabled> -cid <clientId> -cs <clientSecret> [-asr <allowSelfRegistration>] [-dgid <defaultGroupRtId>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-n` | `name` | Name (unique) | Yes |
| `-t` | `tenantId` | Azure Entra ID tenant ID | Yes |
| `-e` | `enabled` | `true` or `false` | Yes |
| `-cid` | `clientId` | Client ID from Azure | Yes |
| `-cs` | `clientSecret` | Client secret from Azure | Yes |
| `-asr` | `allowSelfRegistration` | Allow self-registration (`true`/`false`) | No |
| `-dgid` | `defaultGroupRtId` | Default group RtId for new users | No |

#### AddOctoTenantIdentityProvider
Cross-tenant authentication: allows users from a parent tenant to authenticate.
```
octo-cli -c AddOctoTenantIdentityProvider -n <name> -e <enabled> -ptid <parentTenantId> [-asr <allowSelfRegistration>] [-dgid <defaultGroupRtId>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-n` | `name` | Name (unique) | Yes |
| `-e` | `enabled` | `true` or `false` | Yes |
| `-ptid` | `parentTenantId` | Parent tenant ID for cross-tenant auth | Yes |
| `-asr` | `allowSelfRegistration` | Allow self-registration (`true`/`false`) | No |
| `-dgid` | `defaultGroupRtId` | Default group RtId for new users | No |

#### UpdateIdentityProvider
```
octo-cli -c UpdateIdentityProvider -id <identifier> [-n <name>] [-e <enabled>] [-cid <clientId>] [-cs <clientSecret>] [-asr <allowSelfRegistration>] [-dgid <defaultGroupRtId>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-id` | `identifier` | ID of identity provider | Yes |
| `-n` | `name` | Name (unique) | No |
| `-e` | `enabled` | `true` or `false` | No |
| `-cid` | `clientId` | Client ID | No |
| `-cs` | `clientSecret` | Client secret | No |
| `-asr` | `allowSelfRegistration` | Allow self-registration (`true`/`false`) | No |
| `-dgid` | `defaultGroupRtId` | Default group RtId for new users | No |

#### DeleteIdentityProvider
```
octo-cli -c DeleteIdentityProvider -id <identifier> [-y]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-id` | `identifier` | ID of identity provider | Yes |
| `-y` | `yes` | Skip confirmation prompt | No |

### API Scopes

#### GetApiScopes
Lists all API scopes. No arguments.
```
octo-cli -c GetApiScopes
```

#### CreateApiScope
```
octo-cli -c CreateApiScope -n <name> [-e <enabled>] [-dn <displayName>] [-d <description>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-n` | `name` | Scope name (unique) | Yes |
| `-e` | `enabled` | `true` or `false` | No |
| `-dn` | `displayName` | Display name | No |
| `-d` | `description` | Description | No |

#### UpdateApiScope
```
octo-cli -c UpdateApiScope -n <name> [-nn <newName>] [-e <enabled>] [-dn <displayName>] [-d <description>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-n` | `name` | Current scope name | Yes |
| `-nn` | `newName` | New scope name | No |
| `-e` | `enabled` | `true` or `false` | No |
| `-dn` | `displayName` | Display name | No |
| `-d` | `description` | Description | No |

#### DeleteApiScope
```
octo-cli -c DeleteApiScope -n <name> [-y]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-n` | `name` | Scope name | Yes |
| `-y` | `yes` | Skip confirmation prompt | No |

### API Resources

#### GetApiResources
Lists all API resources. No arguments.
```
octo-cli -c GetApiResources
```

#### CreateApiResource
```
octo-cli -c CreateApiResource -n <name> [-dn <displayName>] [-d <description>] [-s <scopes>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-n` | `name` | Resource name (unique) | Yes |
| `-dn` | `displayName` | Display name | No |
| `-d` | `description` | Description | No |
| `-s` | `scopes` | Comma-separated scopes | No |

#### UpdateApiResource
```
octo-cli -c UpdateApiResource -n <name> [-dn <displayName>] [-d <description>] [-s <scopes>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-n` | `name` | Resource name | Yes |
| `-dn` | `displayName` | Display name | No |
| `-d` | `description` | Description | No |
| `-s` | `scopes` | Comma-separated scopes | No |

#### DeleteApiResource
```
octo-cli -c DeleteApiResource -n <name> [-y]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-n` | `name` | Resource name | Yes |
| `-y` | `yes` | Skip confirmation prompt | No |

### API Secrets

#### GetApiSecretsApiResource
```
octo-cli -c GetApiSecretsApiResource -n <name>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-n` | `name` | API resource name | Yes |

#### GetApiSecretsClient
```
octo-cli -c GetApiSecretsClient -cid <clientId>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-cid` | `clientId` | Client ID | Yes |

#### CreateApiSecretApiResource
```
octo-cli -c CreateApiSecretApiResource -n <name> [-e <expirationDate>] [-d <description>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-n` | `name` | API resource name | Yes |
| `-e` | `expirationDate` | Expiration date | No |
| `-d` | `description` | Description | No |

#### CreateApiSecretClient
```
octo-cli -c CreateApiSecretClient -cid <clientId> [-e <expirationDate>] [-d <description>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-cid` | `clientId` | Client ID | Yes |
| `-e` | `expirationDate` | Expiration date | No |
| `-d` | `description` | Description | No |

#### UpdateApiSecretApiResource
```
octo-cli -c UpdateApiSecretApiResource -n <name> -s <secretValue> [-e <expirationDate>] [-d <description>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-n` | `name` | API resource name | Yes |
| `-s` | `secretValue` | Secret value (sha256 encoded) | Yes |
| `-e` | `expirationDate` | Expiration date | No |
| `-d` | `description` | Description | No |

#### UpdateApiSecretClient
```
octo-cli -c UpdateApiSecretClient -cid <clientId> -s <secretValue> [-e <expirationDate>] [-d <description>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-cid` | `clientId` | Client ID | Yes |
| `-s` | `secretValue` | Secret value (sha256 encoded) | Yes |
| `-e` | `expirationDate` | Expiration date | No |
| `-d` | `description` | Description | No |

#### DeleteApiSecretApiResource
```
octo-cli -c DeleteApiSecretApiResource -n <name> -s <secretValue> [-y]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-n` | `name` | API resource name | Yes |
| `-s` | `secretValue` | Secret value (sha256) | Yes |
| `-y` | `yes` | Skip confirmation prompt | No |

#### DeleteApiSecretClient
```
octo-cli -c DeleteApiSecretClient -cid <clientId> -s <secretValue> [-y]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-cid` | `clientId` | Client ID | Yes |
| `-s` | `secretValue` | Secret value (sha256) | Yes |
| `-y` | `yes` | Skip confirmation prompt | No |

### Groups

#### GetGroups
Lists all groups. No arguments.
```
octo-cli -c GetGroups
```

#### GetGroup
```
octo-cli -c GetGroup -id <identifier>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-id` | `identifier` | Group ID | Yes |

#### CreateGroup
```
octo-cli -c CreateGroup -n <name> [-d <description>] [-rids <roleIds>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-n` | `name` | Group name | Yes |
| `-d` | `description` | Description | No |
| `-rids` | `roleIds` | Comma-separated role IDs | No |

#### UpdateGroup
```
octo-cli -c UpdateGroup -id <identifier> -n <name> [-d <description>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-id` | `identifier` | Group ID | Yes |
| `-n` | `name` | Group name | Yes |
| `-d` | `description` | Description | No |

#### DeleteGroup
```
octo-cli -c DeleteGroup -id <identifier>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-id` | `identifier` | Group ID | Yes |

#### UpdateGroupRoles
```
octo-cli -c UpdateGroupRoles -id <identifier> -rids <roleIds>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-id` | `identifier` | Group ID | Yes |
| `-rids` | `roleIds` | Comma-separated role IDs | Yes |

#### AddUserToGroup
```
octo-cli -c AddUserToGroup -id <identifier> -uid <userId>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-id` | `identifier` | Group ID | Yes |
| `-uid` | `userId` | User ID | Yes |

#### RemoveUserFromGroup
```
octo-cli -c RemoveUserFromGroup -id <identifier> -uid <userId>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-id` | `identifier` | Group ID | Yes |
| `-uid` | `userId` | User ID | Yes |

#### AddGroupToGroup
```
octo-cli -c AddGroupToGroup -id <identifier> -cgid <childGroupId>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-id` | `identifier` | Parent group ID | Yes |
| `-cgid` | `childGroupId` | Child group ID to add | Yes |

#### RemoveGroupFromGroup
```
octo-cli -c RemoveGroupFromGroup -id <identifier> -cgid <childGroupId>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-id` | `identifier` | Parent group ID | Yes |
| `-cgid` | `childGroupId` | Child group ID to remove | Yes |

### Email Domain Group Rules

#### GetEmailDomainGroupRules
Lists all email domain group rules. No arguments.
```
octo-cli -c GetEmailDomainGroupRules
```

#### GetEmailDomainGroupRule
```
octo-cli -c GetEmailDomainGroupRule -id <identifier>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-id` | `identifier` | Rule ID | Yes |

#### CreateEmailDomainGroupRule
```
octo-cli -c CreateEmailDomainGroupRule -edp <emailDomainPattern> -tgid <targetGroupRtId> [-d <description>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-edp` | `emailDomainPattern` | Email domain pattern (e.g. `meshmakers.com`) | Yes |
| `-tgid` | `targetGroupRtId` | Target group RtId | Yes |
| `-d` | `description` | Description | No |

#### UpdateEmailDomainGroupRule
```
octo-cli -c UpdateEmailDomainGroupRule -id <identifier> [-edp <emailDomainPattern>] [-tgid <targetGroupRtId>] [-d <description>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-id` | `identifier` | Rule ID | Yes |
| `-edp` | `emailDomainPattern` | Email domain pattern | No |
| `-tgid` | `targetGroupRtId` | Target group RtId | No |
| `-d` | `description` | Description | No |

#### DeleteEmailDomainGroupRule
```
octo-cli -c DeleteEmailDomainGroupRule -id <identifier>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-id` | `identifier` | Rule ID | Yes |

### External Tenant User Mappings

#### GetExternalTenantUserMappings
```
octo-cli -c GetExternalTenantUserMappings -stid <sourceTenantId> [-skip <skip>] [-take <take>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-stid` | `sourceTenantId` | Source tenant ID | Yes |
| `-skip` | `skip` | Number of items to skip | No |
| `-take` | `take` | Number of items to take | No |

#### GetExternalTenantUserMapping
```
octo-cli -c GetExternalTenantUserMapping -id <identifier>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-id` | `identifier` | Mapping ID | Yes |

#### CreateExternalTenantUserMapping
```
octo-cli -c CreateExternalTenantUserMapping -stid <sourceTenantId> -suid <sourceUserId> -sun <sourceUserName> [-rids <roleIds>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-stid` | `sourceTenantId` | Source tenant ID | Yes |
| `-suid` | `sourceUserId` | Source user ID | Yes |
| `-sun` | `sourceUserName` | Source user name | Yes |
| `-rids` | `roleIds` | Comma-separated role IDs | No |

#### UpdateExternalTenantUserMapping
```
octo-cli -c UpdateExternalTenantUserMapping -id <identifier> [-rids <roleIds>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-id` | `identifier` | Mapping ID | Yes |
| `-rids` | `roleIds` | Comma-separated role IDs | No |

#### DeleteExternalTenantUserMapping
```
octo-cli -c DeleteExternalTenantUserMapping -id <identifier>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-id` | `identifier` | Mapping ID | Yes |

### Admin Provisioning

Run from the **system tenant** context (e.g. `local_octosystem`).

#### GetAdminProvisioningMappings
```
octo-cli -c GetAdminProvisioningMappings -ttid <targetTenantId>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-ttid` | `targetTenantId` | Target tenant ID | Yes |

#### CreateAdminProvisioningMapping
```
octo-cli -c CreateAdminProvisioningMapping -ttid <targetTenantId> -stid <sourceTenantId> -suid <sourceUserId> -sun <sourceUserName> [-rids <roleIds>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-ttid` | `targetTenantId` | Target tenant ID | Yes |
| `-stid` | `sourceTenantId` | Source tenant ID | Yes |
| `-suid` | `sourceUserId` | Source user ID | Yes |
| `-sun` | `sourceUserName` | Source user name | Yes |
| `-rids` | `roleIds` | Comma-separated role IDs | No |

#### ProvisionCurrentUser
Provisions the current user as admin in the target tenant.
```
octo-cli -c ProvisionCurrentUser -ttid <targetTenantId>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-ttid` | `targetTenantId` | Target tenant ID | Yes |

#### DeleteAdminProvisioningMapping
```
octo-cli -c DeleteAdminProvisioningMapping -ttid <targetTenantId> -mid <mappingId>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-ttid` | `targetTenantId` | Target tenant ID | Yes |
| `-mid` | `mappingId` | Mapping ID | Yes |

---

## Asset Repository Services

### Tenants

#### GetTenants
Lists all child tenants. No arguments.
```
octo-cli -c GetTenants
```

#### Create
Creates a new tenant and automatically provisions the current user as admin.
```
octo-cli -c Create -tid <tenantId> -db <database> [-np]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-tid` | `tenantId` | Tenant ID | Yes |
| `-db` | `database` | Database name | Yes |
| `-np` | `no-provision` | Skip admin provisioning of the current user (flag, no value) | No |

#### Clean
Resets tenant to factory defaults by deleting CK and RT model.
```
octo-cli -c Clean -tid <tenantId> [-y]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-tid` | `tenantId` | Tenant ID | Yes |
| `-y` | `yes` | Skip confirmation prompt | No |

#### Attach
```
octo-cli -c Attach -tid <tenantId> -db <database>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-tid` | `tenantId` | Tenant ID | Yes |
| `-db` | `database` | Database name | Yes |

#### Detach
```
octo-cli -c Detach -tid <tenantId>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-tid` | `tenantId` | Tenant ID | Yes |

#### Delete
```
octo-cli -c Delete -tid <tenantId> [-y]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-tid` | `tenantId` | Tenant ID | Yes |
| `-y` | `yes` | Skip confirmation prompt | No |

#### ClearCache
```
octo-cli -c ClearCache -tid <tenantId> [-y]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-tid` | `tenantId` | Tenant ID | Yes |
| `-y` | `yes` | Skip confirmation prompt | No |

#### UpdateSystemCkModel
```
octo-cli -c UpdateSystemCkModel -tid <tenantId>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-tid` | `tenantId` | Tenant ID | Yes |

### Models

#### ImportCk
Schedules import job for construction kit files. To wait for the job to complete, use `-w`.
```
octo-cli -c ImportCk -f <file> [-w]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-f` | `file` | File to import | Yes |
| `-w` | `wait` | Wait for import job to complete | No |

#### ImportRt
Schedules import job for runtime model files. To wait for the job to complete, use `-w`.
```
octo-cli -c ImportRt -f <file> [-r] [-w]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-f` | `file` | File to import (YAML format, see below) | Yes |
| `-r` | `replace` | Replace existing entities (flag, no value) | No |
| `-w` | `wait` | Wait for import job to complete | No |

##### ImportRt YAML Format

The import file uses a specific YAML structure. Use `ck_explorer.py preflight <type> --for-import` to generate a template for any CK type with the correct ID format.

```yaml
$schema: https://schemas.meshmakers.cloud/runtime-model.schema.json
dependencies:
  - <ModelName-[major.minor,next-major)>        # e.g. System.Communication-[3.0,4.0)
entities:
  - rtId: <24-hex-character-id>                 # exactly 24 hex chars [0-9a-fA-F]
    ckTypeId: <Model/TypeName-TypeVersion>       # import format (see rules below)
    attributes:
      - id: <Model/AttributeName-AttrVersion>   # full CK attribute ID in import format
        value: <value>
    associations:                               # optional — links to other entities
      - roleId: <Model/RoleName-RoleVersion>    # association role in import format
        targetRtId: <24-hex-id>                 # rtId of the target entity
        targetCkTypeId: <Model/TypeName-TypeVersion>
```

**ImportRt ID format — `ModelName/TypeName-TypeVersion`:**

All IDs in ImportRt YAML (ckTypeId, attribute id, roleId, targetCkTypeId) use the **import format**: model name without version, type/attribute/role name WITH version suffix. This matches the format produced by `ExportRtByDeepGraph`.

| Format | Example | Used in |
|--------|---------|---------|
| Import format (correct for ImportRt) | `System.Communication/Pipeline-1` | ImportRt YAML |
| Fully versioned (from CK explorer) | `System.Communication-3.0.0/Pipeline-1` | ck_explorer.py output |
| Fully unversioned | `System.Communication/Pipeline` | rt_explorer.py input |

**Key rules:**
- **CK type IDs**: `System.Communication/Pipeline-1` (not `System.Communication-3.0.0/Pipeline-1`, not `System.Communication/Pipeline`)
- **Attribute IDs**: `System/Name-1`, `System.Communication/PipelineDefinition-1` (not camelCase property names like `name`)
- **Association role IDs**: `System/ParentChild-1`, `System.Communication/Executes-1`
- **Dependencies** use a version range: `ModelName-[major.minor,next-major)`
- **rtId** must be exactly 24 hex characters matching `^[0-9a-fA-F]{24}$` — letters like `g`-`z` are NOT valid hex

**Example — DataFlow + Pipeline with associations:**

```yaml
$schema: https://schemas.meshmakers.cloud/runtime-model.schema.json
dependencies:
  - System.Communication-[3.0,4.0)
entities:
  - rtId: aaa000000000000000000001
    ckTypeId: System.Communication/DataFlow-1
    attributes:
      - id: System/Name-1
        value: My Data Flow

  - rtId: aaa000000000000000000002
    ckTypeId: System.Communication/Pipeline-1
    associations:
      - roleId: System/ParentChild-1
        targetRtId: aaa000000000000000000001
        targetCkTypeId: System.Communication/DataFlow-1
      - roleId: System.Communication/Executes-1
        targetRtId: <adapter-rtId>
        targetCkTypeId: System.Communication/Adapter-1
    attributes:
      - id: System.Communication/DeploymentState-1
        value: 0
      - id: System/Name-1
        value: My Pipeline
      - id: System/Enabled-1
        value: true
      - id: System.Communication/PipelineDefinition-1
        value: >-
          triggers:
            - type: FromExecutePipelineCommand@1
          transformations:
            - type: GetRtEntitiesByType@1
              ckTypeId: SomeModel/SomeType
              targetPath: $.items
```

**Discovering attribute IDs:** Use `ck_explorer.py preflight <type> --for-import` to generate a ready-to-fill YAML template with the correct CK attribute IDs in import format. The standard preflight output (without `--for-import`) also shows the CK attribute ID alongside each property name.

##### ImportRt Troubleshooting

Import failures return a generic error: `Stream contains invalid runtime model so that the schema validation failed.` This message does not indicate which entity or field caused the failure. Common causes:

- **Wrong ID format:** Using fully versioned IDs (`System.Communication-3.0.0/Pipeline-1`) or fully unversioned IDs (`System.Communication/Pipeline`) instead of the import format (`System.Communication/Pipeline-1`). Use `ck_explorer.py preflight <type> --for-import` to generate the correct format.
- **Wrong CK type name:** Using old/renamed types (e.g., `System.Communication/MeshPipeline` instead of `System.Communication/Pipeline`). Verify type names with `ck_explorer.py types --model <model>`.
- **Wrong attribute ID format:** Using camelCase property names (`pipelineDefinition`) instead of CK attribute IDs (`System.Communication/PipelineDefinition-1`). Use `ck_explorer.py preflight <type> --for-import` to discover correct IDs.
- **Invalid rtId format:** Must be exactly 24 hex characters matching `^[0-9a-fA-F]{24}$`. Letters g-z are NOT hex. The error message gives no indication of which field failed — always validate rtIds before importing.
- **Missing required associations:** Some types require associations (e.g., Pipeline needs ParentChild to DataFlow and Executes to Adapter). Check with `ck_explorer.py preflight <type>`.
- **Missing dependency:** The `dependencies` list must include the CK model(s) used in the file with a valid version range.

**Debugging strategy:** Export an existing working entity with `ExportRtByDeepGraph` and compare the YAML structure to your import file. Try importing entities one at a time to isolate which entity fails.

#### ExportRtByQuery
Exports runtime entities matching a query. **Output is always a ZIP archive** regardless of the file extension specified.
```
octo-cli -c ExportRtByQuery -f <file> -q <queryId>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-f` | `file` | Output file (ZIP archive) | Yes |
| `-q` | `queryId` | Query ID for export | Yes |

#### ExportRtByDeepGraph
Exports runtime entities by following associations from a starting entity. **Output is always a ZIP archive** regardless of the file extension specified — even if you use `.yaml` as the extension, the output is a ZIP containing YAML file(s).
```
octo-cli -c ExportRtByDeepGraph -f <file> -id <runtime-identifiers> -t <ckTypeId>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-f` | `file` | Output file (ZIP archive) | Yes |
| `-id` | `runtime-identifiers` | Semicolon-separated list of RtIds | Yes |
| `-t` | `ckTypeId` | CK type ID as starting point | Yes |

To extract the YAML from the ZIP:
```bash
python3 -c "import zipfile, sys; z=zipfile.ZipFile(sys.argv[1]); [print(z.read(n).decode()) for n in z.namelist()]" export.zip
```

### Time Series

#### EnableStreamData
Enable stream data services for current tenant. No arguments.
```
octo-cli -c EnableStreamData
```

#### DisableStreamData
Disable stream data services for current tenant. No arguments.
```
octo-cli -c DisableStreamData
```

### Fixup Scripts

#### CreateFixupScript
```
octo-cli -c CreateFixupScript -e <enabled> -n <name> -f <file> -o <orderNumber> [-r]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-e` | `enabled` | `true` or `false` | Yes |
| `-n` | `name` | Script name | Yes |
| `-f` | `file` | Script file to import | Yes |
| `-o` | `orderNumber` | Execution order number | Yes |
| `-r` | `replace` | Replace existing script (flag, no value) | No |

---

## Bot Services

### Service Hooks

#### GetServiceHooks
Lists service hooks. No arguments.
```
octo-cli -c GetServiceHooks
```

#### CreateServiceHook
```
octo-cli -c CreateServiceHook -e <enabled> -n <name> -ck <ckId> -f <filter> [-u <uri>] [-a <action>] [-k <apiKey>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-e` | `enabled` | Enabled state | Yes |
| `-n` | `name` | Display name | Yes |
| `-ck` | `ckId` | CK ID the hook applies to | Yes |
| `-f` | `filter` | Filter: `"'AttrName' Operator 'Value'"` (multi-value) | Yes |
| `-u` | `uri` | Base URI of service hook | No |
| `-a` | `action` | Action URI | No |
| `-k` | `apiKey` | API key (HTTP header) | No |

#### UpdateServiceHook
```
octo-cli -c UpdateServiceHook -id <serviceHookId> [-e <enabled>] [-n <name>] [-ck <ckId>] [-f <filter>] [-u <uri>] [-a <action>] [-k <apiKey>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-id` | `serviceHookId` | Service hook ID | Yes |
| `-e` | `enabled` | Enabled state | No |
| `-n` | `name` | Display name | No |
| `-ck` | `ckId` | CK ID | No |
| `-f` | `filter` | Filter (multi-value) | No |
| `-u` | `uri` | Base URI | No |
| `-a` | `action` | Action URI | No |
| `-k` | `apiKey` | API key | No |

#### DeleteServiceHook
```
octo-cli -c DeleteServiceHook -id <serviceHookId>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-id` | `serviceHookId` | Service hook ID | Yes |

### Tenant Backup

#### Dump
Dumps a tenant to a tar.gz file.
```
octo-cli -c Dump -tid <tenantId> -f <file>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-tid` | `tenantId` | Tenant ID | Yes |
| `-f` | `file` | Backup file (*.tar.gz) | Yes |

#### Restore
Restores a tenant from a dump file. To wait for the job to complete, use `-w`.
```
octo-cli -c Restore -tid <tenantId> -db <database> -f <file> [-oldDb <oldDatabaseName>] [-w]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-tid` | `tenantId` | Tenant ID | Yes |
| `-db` | `database` | Database name | Yes |
| `-f` | `file` | Backup file (*.tar.gz) | Yes |
| `-oldDb` | `oldDatabaseName` | Old database name (if different) | No |
| `-w` | `wait` | Wait for restore job to complete | No |

#### RunFixupScripts
Runs fixup scripts for current tenant. To wait for the job to complete, use `-w`.
```
octo-cli -c RunFixupScripts [-w]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-w` | `wait` | Wait for fixup scripts job to complete | No |

---

## Communication Services

All communication commands accept plain runtime object IDs — the SDK handles composite RtEntityId construction internally.

#### EnableCommunication
Enables communication controller for current tenant. No arguments.
```
octo-cli -c EnableCommunication
```

#### DisableCommunication
Disables communication controller for current tenant. No arguments.
```
octo-cli -c DisableCommunication
```

### Adapters

#### GetAdapters
List all adapters for the tenant.
```
octo-cli -c GetAdapters [--json]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `--json` | `json` | Output in JSON format | No |

#### GetAdapter
Get adapter configuration, including linked pipelines.
```
octo-cli -c GetAdapter --identifier <rtId> [--json]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `--identifier` | `identifier` | Runtime object ID of the adapter | Yes |
| `--json` | `json` | Output in JSON format | No |

#### GetAdapterNodes
List all available pipeline node types from connected adapters.
```
octo-cli -c GetAdapterNodes
```
No flags.

#### GetPipelineSchema
Get the JSON Schema describing valid pipeline YAML for an adapter. The schema defines all available node types and their configuration properties.
```
octo-cli -c GetPipelineSchema --adapterId <rtId> [--outputFile <path>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `--adapterId` | `adapterId` | Runtime object ID of the adapter | Yes |
| `--outputFile` | `outputFile` | File path to write the schema to | No |

#### DeployAdapter
Push configuration update to an adapter.
```
octo-cli -c DeployAdapter --identifier <rtId>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `--identifier` | `identifier` | Runtime object ID of the adapter | Yes |

### Pipelines

#### GetPipelineStatus
Get the deployment state of a pipeline.
```
octo-cli -c GetPipelineStatus --identifier <rtId> [--json]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `--identifier` | `identifier` | Runtime object ID of the pipeline | Yes |
| `--json` | `json` | Output in JSON format | No |

#### DeployPipeline
Deploy pipeline YAML to an adapter.
```
octo-cli -c DeployPipeline --adapterId <rtId> --pipelineId <rtId> --file <path>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `--adapterId` | `adapterId` | Runtime object ID of the adapter | Yes |
| `--pipelineId` | `pipelineId` | Runtime object ID of the pipeline | Yes |
| `--file` | `file` | Path to the pipeline YAML file | Yes |

#### ExecutePipeline
Execute a pipeline. Returns an execution ID and metadata.
```
octo-cli -c ExecutePipeline --identifier <rtId> [--inputFile <path>]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `--identifier` | `identifier` | Runtime object ID of the pipeline | Yes |
| `--inputFile` | `inputFile` | Path to JSON file with input data for the execution | No |

#### GetPipelineExecutions
List execution history for a pipeline (status, duration, errors).
```
octo-cli -c GetPipelineExecutions --identifier <rtId> [--json]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `--identifier` | `identifier` | Runtime object ID of the pipeline | Yes |
| `--json` | `json` | Output in JSON format | No |

#### GetLatestPipelineExecution
Get the most recent execution for a pipeline.
```
octo-cli -c GetLatestPipelineExecution --identifier <rtId> [--json]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `--identifier` | `identifier` | Runtime object ID of the pipeline | Yes |
| `--json` | `json` | Output in JSON format | No |

#### GetPipelineDebugPoints
Get the debug node tree for a specific pipeline execution.
```
octo-cli -c GetPipelineDebugPoints --identifier <rtId> --executionId <guid> [--json]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `--identifier` | `identifier` | Runtime object ID of the pipeline | Yes |
| `--executionId` | `executionId` | GUID of the execution to inspect | Yes |
| `--json` | `json` | Output in JSON format | No |

### Triggers

#### DeployTriggers
Deploy all pipeline triggers for the tenant.
```
octo-cli -c DeployTriggers
```
No flags.

#### UndeployTriggers
Undeploy all pipeline triggers for the tenant.
```
octo-cli -c UndeployTriggers
```
No flags.

### Data Flows

#### DeployDataFlow
Deploy a data flow.
```
octo-cli -c DeployDataFlow --identifier <rtId>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `--identifier` | `identifier` | Runtime object ID of the data flow | Yes |

#### UndeployDataFlow
Undeploy a data flow.
```
octo-cli -c UndeployDataFlow --identifier <rtId>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `--identifier` | `identifier` | Runtime object ID of the data flow | Yes |

#### GetDataFlowStatus
Get aggregated status of a data flow, including state, pipeline states, and statistics.
```
octo-cli -c GetDataFlowStatus --identifier <rtId> [--json]
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `--identifier` | `identifier` | Runtime object ID of the data flow | Yes |
| `--json` | `json` | Output in JSON format | No |

---

## Reporting Services

#### EnableReporting
Enables reporting services for current tenant. No arguments.
```
octo-cli -c EnableReporting
```

#### DisableReporting
Disables reporting services for current tenant. No arguments.
```
octo-cli -c DisableReporting
```

---

## Diagnostics

#### ReconfigureLogLevel
```
octo-cli -c ReconfigureLogLevel -n <serviceName> -minL <minLogLevel> -maxL <maxLogLevel> -ln <loggerName>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-n` | `serviceName` | Service: `Identity`, `AssetRepository`, `Bot`, `CommunicationController`, `AdminPanel`, `Reporting` | Yes |
| `-minL` | `minLogLevel` | Min level: `Trace`, `Debug`, `Info`, `Warn`, `Error`, `Fatal`, `Off` | Yes |
| `-maxL` | `maxLogLevel` | Max level: `Trace`, `Debug`, `Info`, `Warn`, `Error`, `Fatal`, `Off` | Yes |
| `-ln` | `loggerName` | Logger: `Microsoft.*`, `Meshmakers.*`, `Masstransit.*`, `*` | Yes |

---

## DevOps

#### GenerateOperatorCertificates
```
octo-cli -c GenerateOperatorCertificates -o <output> -s <serverName> -n <namespace>
```
| Flag | Long | Description | Required |
|---|---|---|---|
| `-o` | `output` | Directory path for certificate output | Yes |
| `-s` | `serverName` | Service/server name (e.g. `octo-mesh-op1-communication-operator`) | Yes |
| `-n` | `namespace` | Namespace (e.g. `octo-operator-system`) | Yes |
