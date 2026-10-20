# Public API for module omni.services.starfleet.auth:

## Classes

- class LauncherUnavailableError(Exception)

- class StarfleetTokenExchangeError(BaseTokenExchangeError)
  - def __init__(self, msg = 'Failed to exchange Starfleet session token', *args, **kwargs)

- class ServiceStarfleetAuthExtension(omni.ext.IExt)
  - NUCLEUS_CLOUD_RE: Unknown
  - def __init__(self)
  - def on_startup(self)
  - def on_shutdown(self)
  - def authenticate(self, omniverse_uri: str) -> str
  - async def authenticate_async(self, nucleus_cloud_host: str) -> str

## Functions

- def log_info(msg)
- def log_warn(msg)
- async def get_starfleet_tokens() -> typing.Tuple[str, str]

## Other

- asyncio: builtin module
- re: builtin module
- omni.client: unknown module
- omni.ext: public module
- WebSocketClient: unknown


# Public API for module omniverse_auth.client:

## Classes

- class ApiToken(Record)
  - name: str

- class AuthStatus
  - OK: str
  - NotFound: str
  - Exists: str
  - Disabled: str
  - Denied: str
  - Expired: str
  - ReadOnly: str
  - UsernameRequired: str
  - NotSupported: str
  - ConnectionError: str
  - InternalError: str
  - InvalidUsername: str
  - UnknownError: str
  - InvalidToken: str
  - Subscribed: str

- class AuthProvider
  - Internal: str
  - NVIDIA: str
  - Starfleet: str
  - Microsoft: str
  - System: str

- class Profile(Record)
  - first_name: Optional[str]
  - last_name: Optional[str]
  - email: Optional[str]
  - admin: Optional[bool]
  - provider: Optional[str]
  - readonly: Optional[bool]
  - nucleus_ro: Optional[bool]
  - enabled: Optional[bool]
  - activated: Optional[bool]

- class UserStoreResult(Record)
  - status: AuthStatus
  - version: int
  - value: Optional[str]

- class Auth(Record)
  - status: AuthStatus
  - version: int
  - access_token: Optional[str]
  - refresh_token: Optional[str]
  - username: Optional[str]
  - profile: Optional[Profile]
  - nonce: Optional[str]

- class GetApiTokens(Record)
  - status: AuthStatus
  - version: int
  - tokens: Optional[List[ApiToken]]

- class DeleteApiToken(Record)
  - status: AuthStatus
  - version: int

- class CreateApiToken(Record)
  - status: AuthStatus
  - version: int
  - token: Optional[str]

- class SSORedirect(Record)
  - status: AuthStatus
  - redirect: str

- class SSOSettings(Record)
  - public_name: str
  - type: str
  - redirect: str
  - image: str
  - version: SSOGetSettingsServerVersion

- class ProfileResponse(Record)
  - status: AuthStatus
  - version: int
  - username: Optional[str]
  - profile: Optional[Profile]

- class ProfileSettings(Record)
  - can_manage: bool
  - version: ProfilesGetSettingsServerVersion

- class CredentialSettings(Record)
  - login_url: Optional[str]
  - can_register: Optional[bool]
  - is_ui_visible: Optional[bool]
  - version: Optional[CredentialsGetSettingsServerVersion]

- class UserStore
  - def __init__(self, transport: Client)
  - async def get(self, key: str, token: str) -> UserStoreResult
  - async def set(self, key: str, value: str, token: str) -> UserStoreResult
  - async def remove(self, key: str, token: str) -> UserStoreResult

- class Tokens
  - def __init__(self, transport: Client)
  - async def generate(self, username: str, admin_token: str) -> Auth
  - async def refresh(self, refresh_token: str) -> Auth
  - async def subscribe(self) -> AsyncIterator[Auth]
  - async def create_api_token(self, access_token: str, name: str) -> CreateApiToken
  - async def delete_api_token(self, access_token: str, name: str) -> DeleteApiToken
  - async def get_api_tokens(self, access_token: str) -> GetApiTokens
  - async def auth_with_api_token(self, api_token: str) -> Auth

- class SSO
  - def __init__(self, transport: Client)
  - async def get_settings(self) -> AsyncIterator[SSOSettings]
  - async def auth(self, type: str, params: SSOParams, nonce: Optional[str] = None) -> Auth
  - async def redirect(self, type: str, state: Optional[str] = None) -> SSORedirect

- class Profiles
  - def __init__(self, transport: Client)
  - async def get_settings(self) -> ProfileSettings
  - async def get_all(self, token: str) -> AsyncIterator[ProfileResponse]
  - async def get(self, username: str) -> ProfileResponse
  - async def set_info(self, username: str, token: str, first_name: Optional[str] = None, last_name: Optional[str] = None, email: Optional[str] = None) -> ProfileResponse
  - async def set_enabled(self, username: str, token: str, enabled: bool) -> ProfileResponse
  - async def set_admin(self, username: str, token: str, admin: bool) -> ProfileResponse
  - async def set_nucleus_ro(self, username: str, token: str, nucleus_ro: bool) -> ProfileResponse
  - async def add(self, username: str, token: str, first_name: Optional[str] = None, last_name: Optional[str] = None, email: Optional[str] = None) -> ProfileResponse

- class Credentials
  - def __init__(self, transport: Client)
  - async def get_settings(self) -> CredentialSettings
  - async def auth(self, username: str, password: str, nonce: Optional[str] = None) -> Auth
  - async def register(self, username: str, password: str, profile: Profile, nonce: Optional[str] = None) -> Auth
  - async def reset(self, username: str, new_password: str, token: str) -> Auth

- class UserStoreGetArgs(Record)
  - version: Literal(UserStoreGetClientVersion)
  - key: str
  - token: str

- class UserStoreSetArgs(Record)
  - version: Literal(UserStoreSetClientVersion)
  - key: str
  - value: str
  - token: str

- class UserStoreRemoveArgs(Record)
  - version: Literal(UserStoreRemoveClientVersion)
  - key: str
  - token: str

- class TokensGenerateArgs(Record)
  - version: Literal(TokensGenerateClientVersion)
  - username: str
  - admin_token: str

- class TokensRefreshArgs(Record)
  - version: Literal(TokensRefreshClientVersion)
  - refresh_token: str

- class TokensSubscribeArgs(Record)
  - version: Literal(TokensSubscribeClientVersion)

- class TokensCreateApiTokenArgs(Record)
  - version: Literal(TokensCreateApiTokenClientVersion)
  - access_token: str
  - name: str

- class TokensDeleteApiTokenArgs(Record)
  - version: Literal(TokensDeleteApiTokenClientVersion)
  - access_token: str
  - name: str

- class TokensGetApiTokensArgs(Record)
  - version: Literal(TokensGetApiTokensClientVersion)
  - access_token: str

- class TokensAuthWithApiTokenArgs(Record)
  - version: Literal(TokensAuthWithApiTokenClientVersion)
  - api_token: str

- class SsoGetSettingsArgs(Record)
  - version: Literal(SSOGetSettingsClientVersion)

- class SsoAuthArgs(Record)
  - version: Literal(SSOAuthClientVersion)
  - type: str
  - params: SSOParams
  - nonce: Optional[str]

- class SsoRedirectArgs(Record)
  - version: Literal(SSORedirectClientVersion)
  - type: str
  - state: Optional[str]

- class ProfilesGetSettingsArgs(Record)
  - version: Literal(ProfilesGetSettingsClientVersion)

- class ProfilesGetAllArgs(Record)
  - version: Literal(ProfilesGetAllClientVersion)
  - token: str

- class ProfilesGetArgs(Record)
  - version: Literal(ProfilesGetClientVersion)
  - username: str

- class ProfilesSetInfoArgs(Record)
  - version: Literal(ProfilesSetInfoClientVersion)
  - username: str
  - token: str
  - first_name: Optional[str]
  - last_name: Optional[str]
  - email: Optional[str]

- class ProfilesSetEnabledArgs(Record)
  - version: Literal(ProfilesSetEnabledClientVersion)
  - username: str
  - token: str
  - enabled: bool

- class ProfilesSetAdminArgs(Record)
  - version: Literal(ProfilesSetAdminClientVersion)
  - username: str
  - token: str
  - admin: bool

- class ProfilesSetNucleusRoArgs(Record)
  - version: Literal(ProfilesSetNucleusRoClientVersion)
  - username: str
  - token: str
  - nucleus_ro: bool

- class ProfilesAddArgs(Record)
  - version: Literal(ProfilesAddClientVersion)
  - username: str
  - token: str
  - first_name: Optional[str]
  - last_name: Optional[str]
  - email: Optional[str]

- class CredentialsGetSettingsArgs(Record)
  - version: Literal(CredentialsGetSettingsClientVersion)

- class CredentialsAuthArgs(Record)
  - version: Literal(CredentialsAuthClientVersion)
  - username: str
  - password: str
  - nonce: Optional[str]

- class CredentialsRegisterArgs(Record)
  - version: Literal(CredentialsRegisterClientVersion)
  - username: str
  - password: str
  - profile: Profile
  - nonce: Optional[str]

- class CredentialsResetArgs(Record)
  - version: Literal(CredentialsResetClientVersion)
  - username: str
  - new_password: str
  - token: str

## Variables

- Capabilities: Unknown
- UserStoreServerRemoteCapabilities: Capabilities
- UserStoreServerLocalCapabilities: Dict
- UserStoreServerCapabilities: UserStoreServerRemoteCapabilities
- UserStoreClientRemoteCapabilities: Capabilities
- UserStoreClientLocalCapabilities: Dict
- UserStoreClientCapabilities: UserStoreClientLocalCapabilities
- UserStoreRemoveServerRemoteVersion: int
- UserStoreRemoveServerLocalVersion: int
- UserStoreRemoveServerVersion: UserStoreRemoveServerRemoteVersion
- UserStoreRemoveClientRemoteVersion: int
- UserStoreRemoveClientLocalVersion: int
- UserStoreSetServerRemoteVersion: int
- UserStoreSetServerLocalVersion: int
- UserStoreSetServerVersion: UserStoreSetServerRemoteVersion
- UserStoreSetClientRemoteVersion: int
- UserStoreSetClientLocalVersion: int
- UserStoreGetServerRemoteVersion: int
- UserStoreGetServerLocalVersion: int
- UserStoreGetServerVersion: UserStoreGetServerRemoteVersion
- UserStoreGetClientRemoteVersion: int
- UserStoreGetClientLocalVersion: int
- TokensServerRemoteCapabilities: Capabilities
- TokensServerLocalCapabilities: Dict
- TokensServerCapabilities: TokensServerRemoteCapabilities
- TokensClientRemoteCapabilities: Capabilities
- TokensClientLocalCapabilities: Dict
- TokensClientCapabilities: TokensClientLocalCapabilities
- TokensAuthWithApiTokenServerRemoteVersion: int
- TokensAuthWithApiTokenServerLocalVersion: int
- TokensAuthWithApiTokenServerVersion: TokensAuthWithApiTokenServerRemoteVersion
- TokensAuthWithApiTokenClientRemoteVersion: int
- TokensAuthWithApiTokenClientLocalVersion: int
- TokensGetApiTokensServerRemoteVersion: int
- TokensGetApiTokensServerLocalVersion: int
- TokensGetApiTokensServerVersion: TokensGetApiTokensServerRemoteVersion
- TokensGetApiTokensClientRemoteVersion: int
- TokensGetApiTokensClientLocalVersion: int
- TokensDeleteApiTokenServerRemoteVersion: int
- TokensDeleteApiTokenServerLocalVersion: int
- TokensDeleteApiTokenServerVersion: TokensDeleteApiTokenServerRemoteVersion
- TokensDeleteApiTokenClientRemoteVersion: int
- TokensDeleteApiTokenClientLocalVersion: int
- TokensCreateApiTokenServerRemoteVersion: int
- TokensCreateApiTokenServerLocalVersion: int
- TokensCreateApiTokenServerVersion: TokensCreateApiTokenServerRemoteVersion
- TokensCreateApiTokenClientRemoteVersion: int
- TokensCreateApiTokenClientLocalVersion: int
- TokensSubscribeServerRemoteVersion: int
- TokensSubscribeServerLocalVersion: int
- TokensSubscribeServerVersion: TokensSubscribeServerRemoteVersion
- TokensSubscribeClientRemoteVersion: int
- TokensSubscribeClientLocalVersion: int
- TokensRefreshServerRemoteVersion: int
- TokensRefreshServerLocalVersion: int
- TokensRefreshServerVersion: TokensRefreshServerRemoteVersion
- TokensRefreshClientRemoteVersion: int
- TokensRefreshClientLocalVersion: int
- TokensGenerateServerRemoteVersion: int
- TokensGenerateServerLocalVersion: int
- TokensGenerateServerVersion: TokensGenerateServerRemoteVersion
- TokensGenerateClientRemoteVersion: int
- TokensGenerateClientLocalVersion: int
- SSOServerRemoteCapabilities: Capabilities
- SSOServerLocalCapabilities: Dict
- SSOServerCapabilities: SSOServerRemoteCapabilities
- SSOClientRemoteCapabilities: Capabilities
- SSOClientLocalCapabilities: Dict
- SSOClientCapabilities: SSOClientLocalCapabilities
- SSORedirectServerRemoteVersion: int
- SSORedirectServerLocalVersion: int
- SSORedirectServerVersion: SSORedirectServerRemoteVersion
- SSORedirectClientRemoteVersion: int
- SSORedirectClientLocalVersion: int
- SSOAuthServerRemoteVersion: int
- SSOAuthServerLocalVersion: int
- SSOAuthServerVersion: SSOAuthServerRemoteVersion
- SSOAuthClientRemoteVersion: int
- SSOAuthClientLocalVersion: int
- SSOGetSettingsServerRemoteVersion: int
- SSOGetSettingsServerLocalVersion: int
- SSOGetSettingsClientRemoteVersion: int
- SSOGetSettingsClientLocalVersion: int
- ProfilesServerRemoteCapabilities: Capabilities
- ProfilesServerLocalCapabilities: Dict
- ProfilesServerCapabilities: ProfilesServerRemoteCapabilities
- ProfilesClientRemoteCapabilities: Capabilities
- ProfilesClientLocalCapabilities: Dict
- ProfilesClientCapabilities: ProfilesClientLocalCapabilities
- ProfilesAddServerRemoteVersion: int
- ProfilesAddServerLocalVersion: int
- ProfilesAddServerVersion: ProfilesAddServerRemoteVersion
- ProfilesAddClientRemoteVersion: int
- ProfilesAddClientLocalVersion: int
- ProfilesSetNucleusRoServerRemoteVersion: int
- ProfilesSetNucleusRoServerLocalVersion: int
- ProfilesSetNucleusRoServerVersion: ProfilesSetNucleusRoServerRemoteVersion
- ProfilesSetNucleusRoClientRemoteVersion: int
- ProfilesSetNucleusRoClientLocalVersion: int
- ProfilesSetAdminServerRemoteVersion: int
- ProfilesSetAdminServerLocalVersion: int
- ProfilesSetAdminServerVersion: ProfilesSetAdminServerRemoteVersion
- ProfilesSetAdminClientRemoteVersion: int
- ProfilesSetAdminClientLocalVersion: int
- ProfilesSetEnabledServerRemoteVersion: int
- ProfilesSetEnabledServerLocalVersion: int
- ProfilesSetEnabledServerVersion: ProfilesSetEnabledServerRemoteVersion
- ProfilesSetEnabledClientRemoteVersion: int
- ProfilesSetEnabledClientLocalVersion: int
- ProfilesSetInfoServerRemoteVersion: int
- ProfilesSetInfoServerLocalVersion: int
- ProfilesSetInfoServerVersion: ProfilesSetInfoServerRemoteVersion
- ProfilesSetInfoClientRemoteVersion: int
- ProfilesSetInfoClientLocalVersion: int
- ProfilesGetServerRemoteVersion: int
- ProfilesGetServerLocalVersion: int
- ProfilesGetServerVersion: ProfilesGetServerRemoteVersion
- ProfilesGetClientRemoteVersion: int
- ProfilesGetClientLocalVersion: int
- ProfilesGetAllServerRemoteVersion: int
- ProfilesGetAllServerLocalVersion: int
- ProfilesGetAllServerVersion: ProfilesGetAllServerRemoteVersion
- ProfilesGetAllClientRemoteVersion: int
- ProfilesGetAllClientLocalVersion: int
- ProfilesGetSettingsServerRemoteVersion: int
- ProfilesGetSettingsServerLocalVersion: int
- ProfilesGetSettingsClientRemoteVersion: int
- ProfilesGetSettingsClientLocalVersion: int
- CredentialsServerRemoteCapabilities: Capabilities
- CredentialsServerLocalCapabilities: Dict
- CredentialsServerCapabilities: CredentialsServerRemoteCapabilities
- CredentialsClientRemoteCapabilities: Capabilities
- CredentialsClientLocalCapabilities: Dict
- CredentialsClientCapabilities: CredentialsClientLocalCapabilities
- CredentialsResetServerRemoteVersion: int
- CredentialsResetServerLocalVersion: int
- CredentialsResetServerVersion: CredentialsResetServerRemoteVersion
- CredentialsResetClientRemoteVersion: int
- CredentialsResetClientLocalVersion: int
- CredentialsRegisterServerRemoteVersion: int
- CredentialsRegisterServerLocalVersion: int
- CredentialsRegisterServerVersion: CredentialsRegisterServerRemoteVersion
- CredentialsRegisterClientRemoteVersion: int
- CredentialsRegisterClientLocalVersion: int
- CredentialsAuthServerRemoteVersion: int
- CredentialsAuthServerLocalVersion: int
- CredentialsAuthServerVersion: CredentialsAuthServerRemoteVersion
- CredentialsAuthClientRemoteVersion: int
- CredentialsAuthClientLocalVersion: int
- CredentialsGetSettingsServerRemoteVersion: int
- CredentialsGetSettingsServerLocalVersion: int
- CredentialsGetSettingsClientRemoteVersion: int
- CredentialsGetSettingsClientLocalVersion: int
- SSOGetSettingsServerVersion: SSOGetSettingsServerRemoteVersion
- ProfilesGetSettingsServerVersion: ProfilesGetSettingsServerRemoteVersion
- CredentialsGetSettingsServerVersion: CredentialsGetSettingsServerRemoteVersion
- UserStoreRemoveClientVersion: UserStoreRemoveClientLocalVersion
- UserStoreSetClientVersion: UserStoreSetClientLocalVersion
- UserStoreGetClientVersion: UserStoreGetClientLocalVersion
- TokensAuthWithApiTokenClientVersion: TokensAuthWithApiTokenClientLocalVersion
- TokensGetApiTokensClientVersion: TokensGetApiTokensClientLocalVersion
- TokensDeleteApiTokenClientVersion: TokensDeleteApiTokenClientLocalVersion
- TokensCreateApiTokenClientVersion: TokensCreateApiTokenClientLocalVersion
- TokensSubscribeClientVersion: TokensSubscribeClientLocalVersion
- TokensRefreshClientVersion: TokensRefreshClientLocalVersion
- TokensGenerateClientVersion: TokensGenerateClientLocalVersion
- SSORedirectClientVersion: SSORedirectClientLocalVersion
- SSOParams: Unknown
- SSOAuthClientVersion: SSOAuthClientLocalVersion
- SSOGetSettingsClientVersion: SSOGetSettingsClientLocalVersion
- ProfilesAddClientVersion: ProfilesAddClientLocalVersion
- ProfilesSetNucleusRoClientVersion: ProfilesSetNucleusRoClientLocalVersion
- ProfilesSetAdminClientVersion: ProfilesSetAdminClientLocalVersion
- ProfilesSetEnabledClientVersion: ProfilesSetEnabledClientLocalVersion
- ProfilesSetInfoClientVersion: ProfilesSetInfoClientLocalVersion
- ProfilesGetClientVersion: ProfilesGetClientLocalVersion
- ProfilesGetAllClientVersion: ProfilesGetAllClientLocalVersion
- ProfilesGetSettingsClientVersion: ProfilesGetSettingsClientLocalVersion
- CredentialsResetClientVersion: CredentialsResetClientLocalVersion
- CredentialsRegisterClientVersion: CredentialsRegisterClientLocalVersion
- CredentialsAuthClientVersion: CredentialsAuthClientLocalVersion
- CredentialsGetSettingsClientVersion: CredentialsGetSettingsClientLocalVersion

## Other

- AsyncIterator: unknown
- Dict: unknown
- List: unknown
- Optional: unknown
- Client: unknown
- Literal: unknown
- Record: unknown
- Enum: unknown


# Public API for module omniverse_auth.data:

## Classes

- class ApiToken(Record)
  - name: str

- class AuthStatus
  - OK: str
  - NotFound: str
  - Exists: str
  - Disabled: str
  - Denied: str
  - Expired: str
  - ReadOnly: str
  - UsernameRequired: str
  - NotSupported: str
  - ConnectionError: str
  - InternalError: str
  - InvalidUsername: str
  - UnknownError: str
  - InvalidToken: str
  - Subscribed: str

- class AuthProvider
  - Internal: str
  - NVIDIA: str
  - Starfleet: str
  - Microsoft: str
  - System: str

- class Profile(Record)
  - first_name: Optional[str]
  - last_name: Optional[str]
  - email: Optional[str]
  - admin: Optional[bool]
  - provider: Optional[str]
  - readonly: Optional[bool]
  - nucleus_ro: Optional[bool]
  - enabled: Optional[bool]
  - activated: Optional[bool]

- class UserStoreResult(Record)
  - status: AuthStatus
  - version: int
  - value: Optional[str]

- class Auth(Record)
  - status: AuthStatus
  - version: int
  - access_token: Optional[str]
  - refresh_token: Optional[str]
  - username: Optional[str]
  - profile: Optional[Profile]
  - nonce: Optional[str]

- class GetApiTokens(Record)
  - status: AuthStatus
  - version: int
  - tokens: Optional[List[ApiToken]]

- class DeleteApiToken(Record)
  - status: AuthStatus
  - version: int

- class CreateApiToken(Record)
  - status: AuthStatus
  - version: int
  - token: Optional[str]

- class SSORedirect(Record)
  - status: AuthStatus
  - redirect: str

- class SSOSettings(Record)
  - public_name: str
  - type: str
  - redirect: str
  - image: str
  - version: SSOGetSettingsServerVersion

- class ProfileResponse(Record)
  - status: AuthStatus
  - version: int
  - username: Optional[str]
  - profile: Optional[Profile]

- class ProfileSettings(Record)
  - can_manage: bool
  - version: ProfilesGetSettingsServerVersion

- class CredentialSettings(Record)
  - login_url: Optional[str]
  - can_register: Optional[bool]
  - is_ui_visible: Optional[bool]
  - version: Optional[CredentialsGetSettingsServerVersion]

## Variables

- Capabilities: Unknown
- UserStoreServerRemoteCapabilities: Capabilities
- UserStoreServerLocalCapabilities: Dict
- UserStoreServerCapabilities: UserStoreServerRemoteCapabilities
- UserStoreClientRemoteCapabilities: Capabilities
- UserStoreClientLocalCapabilities: Dict
- UserStoreClientCapabilities: UserStoreClientLocalCapabilities
- UserStoreRemoveServerRemoteVersion: int
- UserStoreRemoveServerLocalVersion: int
- UserStoreRemoveServerVersion: UserStoreRemoveServerRemoteVersion
- UserStoreRemoveClientRemoteVersion: int
- UserStoreRemoveClientLocalVersion: int
- UserStoreSetServerRemoteVersion: int
- UserStoreSetServerLocalVersion: int
- UserStoreSetServerVersion: UserStoreSetServerRemoteVersion
- UserStoreSetClientRemoteVersion: int
- UserStoreSetClientLocalVersion: int
- UserStoreGetServerRemoteVersion: int
- UserStoreGetServerLocalVersion: int
- UserStoreGetServerVersion: UserStoreGetServerRemoteVersion
- UserStoreGetClientRemoteVersion: int
- UserStoreGetClientLocalVersion: int
- TokensServerRemoteCapabilities: Capabilities
- TokensServerLocalCapabilities: Dict
- TokensServerCapabilities: TokensServerRemoteCapabilities
- TokensClientRemoteCapabilities: Capabilities
- TokensClientLocalCapabilities: Dict
- TokensClientCapabilities: TokensClientLocalCapabilities
- TokensAuthWithApiTokenServerRemoteVersion: int
- TokensAuthWithApiTokenServerLocalVersion: int
- TokensAuthWithApiTokenServerVersion: TokensAuthWithApiTokenServerRemoteVersion
- TokensAuthWithApiTokenClientRemoteVersion: int
- TokensAuthWithApiTokenClientLocalVersion: int
- TokensGetApiTokensServerRemoteVersion: int
- TokensGetApiTokensServerLocalVersion: int
- TokensGetApiTokensServerVersion: TokensGetApiTokensServerRemoteVersion
- TokensGetApiTokensClientRemoteVersion: int
- TokensGetApiTokensClientLocalVersion: int
- TokensDeleteApiTokenServerRemoteVersion: int
- TokensDeleteApiTokenServerLocalVersion: int
- TokensDeleteApiTokenServerVersion: TokensDeleteApiTokenServerRemoteVersion
- TokensDeleteApiTokenClientRemoteVersion: int
- TokensDeleteApiTokenClientLocalVersion: int
- TokensCreateApiTokenServerRemoteVersion: int
- TokensCreateApiTokenServerLocalVersion: int
- TokensCreateApiTokenServerVersion: TokensCreateApiTokenServerRemoteVersion
- TokensCreateApiTokenClientRemoteVersion: int
- TokensCreateApiTokenClientLocalVersion: int
- TokensSubscribeServerRemoteVersion: int
- TokensSubscribeServerLocalVersion: int
- TokensSubscribeServerVersion: TokensSubscribeServerRemoteVersion
- TokensSubscribeClientRemoteVersion: int
- TokensSubscribeClientLocalVersion: int
- TokensRefreshServerRemoteVersion: int
- TokensRefreshServerLocalVersion: int
- TokensRefreshServerVersion: TokensRefreshServerRemoteVersion
- TokensRefreshClientRemoteVersion: int
- TokensRefreshClientLocalVersion: int
- TokensGenerateServerRemoteVersion: int
- TokensGenerateServerLocalVersion: int
- TokensGenerateServerVersion: TokensGenerateServerRemoteVersion
- TokensGenerateClientRemoteVersion: int
- TokensGenerateClientLocalVersion: int
- SSOServerRemoteCapabilities: Capabilities
- SSOServerLocalCapabilities: Dict
- SSOServerCapabilities: SSOServerRemoteCapabilities
- SSOClientRemoteCapabilities: Capabilities
- SSOClientLocalCapabilities: Dict
- SSOClientCapabilities: SSOClientLocalCapabilities
- SSORedirectServerRemoteVersion: int
- SSORedirectServerLocalVersion: int
- SSORedirectServerVersion: SSORedirectServerRemoteVersion
- SSORedirectClientRemoteVersion: int
- SSORedirectClientLocalVersion: int
- SSOAuthServerRemoteVersion: int
- SSOAuthServerLocalVersion: int
- SSOAuthServerVersion: SSOAuthServerRemoteVersion
- SSOAuthClientRemoteVersion: int
- SSOAuthClientLocalVersion: int
- SSOGetSettingsServerRemoteVersion: int
- SSOGetSettingsServerLocalVersion: int
- SSOGetSettingsClientRemoteVersion: int
- SSOGetSettingsClientLocalVersion: int
- ProfilesServerRemoteCapabilities: Capabilities
- ProfilesServerLocalCapabilities: Dict
- ProfilesServerCapabilities: ProfilesServerRemoteCapabilities
- ProfilesClientRemoteCapabilities: Capabilities
- ProfilesClientLocalCapabilities: Dict
- ProfilesClientCapabilities: ProfilesClientLocalCapabilities
- ProfilesAddServerRemoteVersion: int
- ProfilesAddServerLocalVersion: int
- ProfilesAddServerVersion: ProfilesAddServerRemoteVersion
- ProfilesAddClientRemoteVersion: int
- ProfilesAddClientLocalVersion: int
- ProfilesSetNucleusRoServerRemoteVersion: int
- ProfilesSetNucleusRoServerLocalVersion: int
- ProfilesSetNucleusRoServerVersion: ProfilesSetNucleusRoServerRemoteVersion
- ProfilesSetNucleusRoClientRemoteVersion: int
- ProfilesSetNucleusRoClientLocalVersion: int
- ProfilesSetAdminServerRemoteVersion: int
- ProfilesSetAdminServerLocalVersion: int
- ProfilesSetAdminServerVersion: ProfilesSetAdminServerRemoteVersion
- ProfilesSetAdminClientRemoteVersion: int
- ProfilesSetAdminClientLocalVersion: int
- ProfilesSetEnabledServerRemoteVersion: int
- ProfilesSetEnabledServerLocalVersion: int
- ProfilesSetEnabledServerVersion: ProfilesSetEnabledServerRemoteVersion
- ProfilesSetEnabledClientRemoteVersion: int
- ProfilesSetEnabledClientLocalVersion: int
- ProfilesSetInfoServerRemoteVersion: int
- ProfilesSetInfoServerLocalVersion: int
- ProfilesSetInfoServerVersion: ProfilesSetInfoServerRemoteVersion
- ProfilesSetInfoClientRemoteVersion: int
- ProfilesSetInfoClientLocalVersion: int
- ProfilesGetServerRemoteVersion: int
- ProfilesGetServerLocalVersion: int
- ProfilesGetServerVersion: ProfilesGetServerRemoteVersion
- ProfilesGetClientRemoteVersion: int
- ProfilesGetClientLocalVersion: int
- ProfilesGetAllServerRemoteVersion: int
- ProfilesGetAllServerLocalVersion: int
- ProfilesGetAllServerVersion: ProfilesGetAllServerRemoteVersion
- ProfilesGetAllClientRemoteVersion: int
- ProfilesGetAllClientLocalVersion: int
- ProfilesGetSettingsServerRemoteVersion: int
- ProfilesGetSettingsServerLocalVersion: int
- ProfilesGetSettingsClientRemoteVersion: int
- ProfilesGetSettingsClientLocalVersion: int
- CredentialsServerRemoteCapabilities: Capabilities
- CredentialsServerLocalCapabilities: Dict
- CredentialsServerCapabilities: CredentialsServerRemoteCapabilities
- CredentialsClientRemoteCapabilities: Capabilities
- CredentialsClientLocalCapabilities: Dict
- CredentialsClientCapabilities: CredentialsClientLocalCapabilities
- CredentialsResetServerRemoteVersion: int
- CredentialsResetServerLocalVersion: int
- CredentialsResetServerVersion: CredentialsResetServerRemoteVersion
- CredentialsResetClientRemoteVersion: int
- CredentialsResetClientLocalVersion: int
- CredentialsRegisterServerRemoteVersion: int
- CredentialsRegisterServerLocalVersion: int
- CredentialsRegisterServerVersion: CredentialsRegisterServerRemoteVersion
- CredentialsRegisterClientRemoteVersion: int
- CredentialsRegisterClientLocalVersion: int
- CredentialsAuthServerRemoteVersion: int
- CredentialsAuthServerLocalVersion: int
- CredentialsAuthServerVersion: CredentialsAuthServerRemoteVersion
- CredentialsAuthClientRemoteVersion: int
- CredentialsAuthClientLocalVersion: int
- CredentialsGetSettingsServerRemoteVersion: int
- CredentialsGetSettingsServerLocalVersion: int
- CredentialsGetSettingsClientRemoteVersion: int
- CredentialsGetSettingsClientLocalVersion: int
- SSOGetSettingsServerVersion: SSOGetSettingsServerRemoteVersion
- ProfilesGetSettingsServerVersion: ProfilesGetSettingsServerRemoteVersion
- CredentialsGetSettingsServerVersion: CredentialsGetSettingsServerRemoteVersion
- UserStoreRemoveClientVersion: UserStoreRemoveClientLocalVersion
- UserStoreSetClientVersion: UserStoreSetClientLocalVersion
- UserStoreGetClientVersion: UserStoreGetClientLocalVersion
- TokensAuthWithApiTokenClientVersion: TokensAuthWithApiTokenClientLocalVersion
- TokensGetApiTokensClientVersion: TokensGetApiTokensClientLocalVersion
- TokensDeleteApiTokenClientVersion: TokensDeleteApiTokenClientLocalVersion
- TokensCreateApiTokenClientVersion: TokensCreateApiTokenClientLocalVersion
- TokensSubscribeClientVersion: TokensSubscribeClientLocalVersion
- TokensRefreshClientVersion: TokensRefreshClientLocalVersion
- TokensGenerateClientVersion: TokensGenerateClientLocalVersion
- SSORedirectClientVersion: SSORedirectClientLocalVersion
- SSOParams: Unknown
- SSOAuthClientVersion: SSOAuthClientLocalVersion
- SSOGetSettingsClientVersion: SSOGetSettingsClientLocalVersion
- ProfilesAddClientVersion: ProfilesAddClientLocalVersion
- ProfilesSetNucleusRoClientVersion: ProfilesSetNucleusRoClientLocalVersion
- ProfilesSetAdminClientVersion: ProfilesSetAdminClientLocalVersion
- ProfilesSetEnabledClientVersion: ProfilesSetEnabledClientLocalVersion
- ProfilesSetInfoClientVersion: ProfilesSetInfoClientLocalVersion
- ProfilesGetClientVersion: ProfilesGetClientLocalVersion
- ProfilesGetAllClientVersion: ProfilesGetAllClientLocalVersion
- ProfilesGetSettingsClientVersion: ProfilesGetSettingsClientLocalVersion
- CredentialsResetClientVersion: CredentialsResetClientLocalVersion
- CredentialsRegisterClientVersion: CredentialsRegisterClientLocalVersion
- CredentialsAuthClientVersion: CredentialsAuthClientLocalVersion
- CredentialsGetSettingsClientVersion: CredentialsGetSettingsClientLocalVersion

## Other

- List: unknown
- Optional: unknown
- Dict: unknown
- AsyncIterator: unknown
- Enum: unknown
- Record: unknown
- Literal: unknown

# Public API for module omniverse_auth:

## Other

- UNKNOWN_MODULE_DEFS: unknown
