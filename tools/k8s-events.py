from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

class K8sEventsTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        namespace = (tool_parameters.get("namespace") or "").strip() or None
        limit = tool_parameters.get("limit")
        try:
            limit_n = int(limit) if limit is not None else None
        except Exception:
            limit_n = None
        kubeconfig_param = self.runtime.credentials.get("kubeconfig")
        try:
            api_client, _ = self._build_api_client(kubeconfig_param)
            from kubernetes import client
            events = []
            try:
                ev = client.EventsV1Api(api_client)
                objs = (ev.list_namespaced_event(namespace=namespace).items if namespace else ev.list_event_for_all_namespaces().items)
                for e in objs:
                    events.append({
                        "namespace": e.metadata.namespace,
                        "reason": e.reason,
                        "note": e.note,
                        "type": e.type,
                        "regarding": {
                            "kind": getattr(e.regarding, "kind", None),
                            "name": getattr(e.regarding, "name", None),
                        },
                        "eventTime": str(getattr(e, "event_time", "")),
                    })
            except Exception:
                core = client.CoreV1Api(api_client)
                objs = (core.list_namespaced_event(namespace=namespace).items if namespace else core.list_event_for_all_namespaces().items)
                for e in objs:
                    involved = getattr(e, "involved_object", None)
                    events.append({
                        "namespace": e.metadata.namespace,
                        "reason": e.reason,
                        "message": e.message,
                        "type": e.type,
                        "involvedObject": {
                            "kind": getattr(involved, "kind", None),
                            "name": getattr(involved, "name", None),
                        },
                        "lastTimestamp": str(getattr(e, "last_timestamp", "")),
                    })
            if limit_n is not None:
                events = events[:max(limit_n, 0)]
            j = {"events": events}
            j.update(self._time_info())
            yield self.create_json_message(j)
            yield self.create_text_message(self._append_time(f"Events count={len(events)}"))
        except Exception as e:
            try:
                from kubernetes.client.rest import ApiException
                if isinstance(e, ApiException):
                    yield self.create_text_message(self._append_time(f"Error: status={e.status} reason={e.reason}"))
                    b = (e.body or "")
                    yield self.create_text_message(self._append_time(str(b)[:500]))
                    return
            except Exception:
                pass
            yield self.create_text_message(self._append_time(f"Error: {str(e)}"))

    def _build_api_client(self, kubeconfig_param: Any):
        from kubernetes import client, config
        import yaml
        import os
        import base64
        if isinstance(kubeconfig_param, dict):
            if "path" in kubeconfig_param and isinstance(kubeconfig_param["path"], str) and os.path.exists(kubeconfig_param["path"]):
                config.load_kube_config(config_file=kubeconfig_param["path"])
                tls_mode = (self.runtime.credentials.get("tlsMode") or os.environ.get("K8S_TLS_MODE") or "strict")
                cfg = client.Configuration.get_default_copy()
                if tls_mode == "skip-hostname":
                    try:
                        cfg.assert_hostname = False
                    except Exception:
                        pass
                elif tls_mode == "insecure":
                    cfg.verify_ssl = False
                    try:
                        cfg.assert_hostname = False
                    except Exception:
                        pass
                return client.ApiClient(configuration=cfg), {"source": "path"}
            if "file" in kubeconfig_param and isinstance(kubeconfig_param["file"], dict):
                p = kubeconfig_param["file"].get("path")
                if isinstance(p, str) and os.path.exists(p):
                    config.load_kube_config(config_file=p)
                    tls_mode = (self.runtime.credentials.get("tlsMode") or os.environ.get("K8S_TLS_MODE") or "strict")
                    cfg = client.Configuration.get_default_copy()
                    if tls_mode == "skip-hostname":
                        try:
                            cfg.assert_hostname = False
                        except Exception:
                            pass
                    elif tls_mode == "insecure":
                        cfg.verify_ssl = False
                        try:
                            cfg.assert_hostname = False
                        except Exception:
                            pass
                    return client.ApiClient(configuration=cfg), {"source": "file.path"}
            if "content" in kubeconfig_param and isinstance(kubeconfig_param["content"], str):
                raw = kubeconfig_param["content"].strip()
                decoded = base64.b64decode(raw).decode("utf-8")
                data = yaml.safe_load(decoded)
                config.load_kube_config_from_dict(data)
                tls_mode = (self.runtime.credentials.get("tlsMode") or os.environ.get("K8S_TLS_MODE") or "strict")
                cfg = client.Configuration.get_default_copy()
                if tls_mode == "skip-hostname":
                    try:
                        cfg.assert_hostname = False
                    except Exception:
                        pass
                elif tls_mode == "insecure":
                    cfg.verify_ssl = False
                    try:
                        cfg.assert_hostname = False
                    except Exception:
                        pass
                return client.ApiClient(configuration=cfg), {"source": "content-base64"}
        if isinstance(kubeconfig_param, str):
            s = kubeconfig_param.strip()
            if os.path.exists(s):
                config.load_kube_config(config_file=s)
                tls_mode = (self.runtime.credentials.get("tlsMode") or os.environ.get("K8S_TLS_MODE") or "strict")
                cfg = client.Configuration.get_default_copy()
                if tls_mode == "skip-hostname":
                    try:
                        cfg.assert_hostname = False
                    except Exception:
                        pass
                elif tls_mode == "insecure":
                    cfg.verify_ssl = False
                    try:
                        cfg.assert_hostname = False
                    except Exception:
                        pass
                return client.ApiClient(configuration=cfg), {"source": "str.path"}
            decoded = base64.b64decode(s).decode("utf-8")
            data = yaml.safe_load(decoded)
            config.load_kube_config_from_dict(data)
            tls_mode = (self.runtime.credentials.get("tlsMode") or os.environ.get("K8S_TLS_MODE") or "strict")
            cfg = client.Configuration.get_default_copy()
            if tls_mode == "skip-hostname":
                try:
                    cfg.assert_hostname = False
                except Exception:
                    pass
            elif tls_mode == "insecure":
                cfg.verify_ssl = False
                try:
                    cfg.assert_hostname = False
                except Exception:
                    pass
            return client.ApiClient(configuration=cfg), {"source": "str.base64"}
        raise ValueError("Invalid kubeconfig")

    def _time_info(self) -> dict[str, str]:
        import datetime
        dt = datetime.datetime.now(datetime.timezone.utc).astimezone()
        tz = dt.tzname() or "local"
        return {"timezone": tz, "time": dt.isoformat()}

    def _append_time(self, text: str) -> str:
        info = self._time_info()
        return f"{text} | timezone={info['timezone']} time={info['time']}"