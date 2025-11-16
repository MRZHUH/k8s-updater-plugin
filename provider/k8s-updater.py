from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError


class K8sUpdaterProvider(ToolProvider):
    
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        try:
            kube = credentials.get("kubeconfig")
            try:
                print(f"provider credential summary: {self._debug_cred_info(kube)}")
            except Exception as _:
                pass
            if not kube:
                raise ValueError("kubeconfig is required")
            valid = False
            if isinstance(kube, dict):
                if kube.get("path"):
                    valid = True
                elif isinstance(kube.get("file"), dict) and kube["file"].get("path"):
                    valid = True
                elif kube.get("content"):
                    c = str(kube.get("content") or "")
                    import base64, yaml
                    try:
                        decoded = base64.b64decode(c).decode("utf-8")
                        d = yaml.safe_load(decoded)
                        if isinstance(d, dict):
                            valid = True
                    except Exception:
                        valid = False
            elif isinstance(kube, str) and kube.strip():
                valid = True
            if not valid:
                raise ValueError("invalid kubeconfig: prefer file upload or path")
        except Exception as e:
            raise ToolProviderCredentialValidationError(str(e))

    def _debug_cred_info(self, v: Any) -> str:
        import os
        try:
            if isinstance(v, dict):
                keys = list(v.keys())
                path = v.get("path") or (v.get("file") or {}).get("path")
                has_content = bool(v.get("content"))
                pe = bool(path and os.path.exists(path))
                return f"type=dict keys={keys} path_exists={pe} has_content={has_content}"
            if isinstance(v, str):
                s = v.strip()
                is_path = os.path.exists(s)
                return f"type=str len={len(s)} is_path={is_path}"
            return f"type={type(v).__name__}"
        except Exception:
            return "unavailable"

    #########################################################################################
    # If OAuth is supported, uncomment the following functions.
    # Warning: please make sure that the sdk version is 0.4.2 or higher.
    #########################################################################################
    # def _oauth_get_authorization_url(self, redirect_uri: str, system_credentials: Mapping[str, Any]) -> str:
    #     """
    #     Generate the authorization URL for k8s-updater OAuth.
    #     """
    #     try:
    #         """
    #         IMPLEMENT YOUR AUTHORIZATION URL GENERATION HERE
    #         """
    #     except Exception as e:
    #         raise ToolProviderOAuthError(str(e))
    #     return ""
        
    # def _oauth_get_credentials(
    #     self, redirect_uri: str, system_credentials: Mapping[str, Any], request: Request
    # ) -> Mapping[str, Any]:
    #     """
    #     Exchange code for access_token.
    #     """
    #     try:
    #         """
    #         IMPLEMENT YOUR CREDENTIALS EXCHANGE HERE
    #         """
    #     except Exception as e:
    #         raise ToolProviderOAuthError(str(e))
    #     return dict()

    # def _oauth_refresh_credentials(
    #     self, redirect_uri: str, system_credentials: Mapping[str, Any], credentials: Mapping[str, Any]
    # ) -> OAuthCredentials:
    #     """
    #     Refresh the credentials
    #     """
    #     return OAuthCredentials(credentials=credentials, expires_at=-1)
