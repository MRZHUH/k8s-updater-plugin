from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

class K8sGetResourceTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        resource_type = (tool_parameters.get("resourceType") or "").strip().lower()
        output_format = ((tool_parameters.get("outputFormat") or "json").strip().lower()) or "json"
        alias = {
            "po": "pod",
            "pod": "pod",
            "no": "node",
            "node": "node",
            "deploy": "deployment",
            "deployment": "deployment",
            "sts": "statefulset",
            "statefulset": "statefulset",
            "ds": "daemonset",
            "daemonset": "daemonset",
            "svc": "service",
            "service": "service",
            "ing": "ingress",
            "ingress": "ingress",
        }
        resource_type = alias.get(resource_type, resource_type)
        name = (tool_parameters.get("name") or "").strip()
        namespace = (tool_parameters.get("namespace") or "").strip() or None
        kubeconfig_param = self.runtime.credentials.get("kubeconfig")
        try:
            api_client, _ = self._build_api_client(kubeconfig_param)
            from kubernetes import client
            if not resource_type:
                yield self.create_text_message(self._append_time("Error: resourceType is required"))
                return
            ns = namespace or "default"
            apps = client.AppsV1Api(api_client)
            core = client.CoreV1Api(api_client)
            net = client.NetworkingV1Api(api_client)
            if resource_type == "deployment":
                if name:
                    obj = apps.read_namespaced_deployment(name=name, namespace=ns)
                    ac = client.ApiClient()
                    data = ac.sanitize_for_serialization(obj)
                    j = {}
                    if output_format == "yaml":
                        import yaml
                        j["yaml"] = yaml.safe_dump(data, sort_keys=False)
                    else:
                        j["object"] = data
                    j.update(self._time_info())
                    yield self.create_json_message(j)
                    yield self.create_text_message(self._append_time(f"Fetched deployment {name} in namespace {ns} format={output_format}"))
                else:
                    objs = apps.list_namespaced_deployment(namespace=ns).items
                    ac = client.ApiClient()
                    items = [ac.sanitize_for_serialization(o) for o in objs]
                    j = {"items": items}
                    j.update(self._time_info())
                    if output_format == "yaml":
                        import yaml
                        j["yaml"] = yaml.safe_dump(items, sort_keys=False)
                    yield self.create_json_message(j)
                    yield self.create_text_message(self._append_time(f"Listed deployments count={len(items)}"))
            elif resource_type == "statefulset":
                if name:
                    obj = apps.read_namespaced_stateful_set(name=name, namespace=ns)
                    ac = client.ApiClient()
                    data = ac.sanitize_for_serialization(obj)
                    j = {}
                    if output_format == "yaml":
                        import yaml
                        j["yaml"] = yaml.safe_dump(data, sort_keys=False)
                    else:
                        j["object"] = data
                    j.update(self._time_info())
                    yield self.create_json_message(j)
                    yield self.create_text_message(self._append_time(f"Fetched statefulset {name} in namespace {ns} format={output_format}"))
                else:
                    objs = apps.list_namespaced_stateful_set(namespace=ns).items
                    ac = client.ApiClient()
                    items = [ac.sanitize_for_serialization(o) for o in objs]
                    j = {"items": items}
                    j.update(self._time_info())
                    if output_format == "yaml":
                        import yaml
                        j["yaml"] = yaml.safe_dump(items, sort_keys=False)
                    yield self.create_json_message(j)
                    yield self.create_text_message(self._append_time(f"Listed statefulsets count={len(items)}"))
            elif resource_type == "daemonset":
                if name:
                    obj = apps.read_namespaced_daemon_set(name=name, namespace=ns)
                    ac = client.ApiClient()
                    data = ac.sanitize_for_serialization(obj)
                    j = {}
                    if output_format == "yaml":
                        import yaml
                        j["yaml"] = yaml.safe_dump(data, sort_keys=False)
                    else:
                        j["object"] = data
                    j.update(self._time_info())
                    yield self.create_json_message(j)
                    yield self.create_text_message(self._append_time(f"Fetched daemonset {name} in namespace {ns} format={output_format}"))
                else:
                    objs = apps.list_namespaced_daemon_set(namespace=ns).items
                    ac = client.ApiClient()
                    items = [ac.sanitize_for_serialization(o) for o in objs]
                    j = {"items": items}
                    j.update(self._time_info())
                    if output_format == "yaml":
                        import yaml
                        j["yaml"] = yaml.safe_dump(items, sort_keys=False)
                    yield self.create_json_message(j)
                    yield self.create_text_message(self._append_time(f"Listed daemonsets count={len(items)}"))
            elif resource_type == "service":
                if name:
                    obj = core.read_namespaced_service(name=name, namespace=ns)
                    ac = client.ApiClient()
                    data = ac.sanitize_for_serialization(obj)
                    j = {}
                    if output_format == "yaml":
                        import yaml
                        j["yaml"] = yaml.safe_dump(data, sort_keys=False)
                    else:
                        j["object"] = data
                    j.update(self._time_info())
                    yield self.create_json_message(j)
                    yield self.create_text_message(self._append_time(f"Fetched service {name} in namespace {ns} format={output_format}"))
                else:
                    objs = core.list_namespaced_service(namespace=ns).items
                    ac = client.ApiClient()
                    items = [ac.sanitize_for_serialization(o) for o in objs]
                    j = {"items": items}
                    j.update(self._time_info())
                    if output_format == "yaml":
                        import yaml
                        j["yaml"] = yaml.safe_dump(items, sort_keys=False)
                    yield self.create_json_message(j)
                    yield self.create_text_message(self._append_time(f"Listed services count={len(items)}"))
            elif resource_type == "ingress":
                if name:
                    obj = net.read_namespaced_ingress(name=name, namespace=ns)
                    ac = client.ApiClient()
                    data = ac.sanitize_for_serialization(obj)
                    j = {}
                    if output_format == "yaml":
                        import yaml
                        j["yaml"] = yaml.safe_dump(data, sort_keys=False)
                    else:
                        j["object"] = data
                    j.update(self._time_info())
                    yield self.create_json_message(j)
                    yield self.create_text_message(self._append_time(f"Fetched ingress {name} in namespace {ns} format={output_format}"))
                else:
                    objs = net.list_namespaced_ingress(namespace=ns).items
                    ac = client.ApiClient()
                    items = [ac.sanitize_for_serialization(o) for o in objs]
                    j = {"items": items}
                    j.update(self._time_info())
                    if output_format == "yaml":
                        import yaml
                        j["yaml"] = yaml.safe_dump(items, sort_keys=False)
                    yield self.create_json_message(j)
                    yield self.create_text_message(self._append_time(f"Listed ingresses count={len(items)}"))
            elif resource_type == "pod":
                if name:
                    obj = core.read_namespaced_pod(name=name, namespace=ns)
                    ac = client.ApiClient()
                    data = ac.sanitize_for_serialization(obj)
                    j = {}
                    if output_format == "yaml":
                        import yaml
                        j["yaml"] = yaml.safe_dump(data, sort_keys=False)
                    else:
                        j["object"] = data
                    j.update(self._time_info())
                    yield self.create_json_message(j)
                    yield self.create_text_message(self._append_time(f"Fetched pod {name} in namespace {ns} format={output_format}"))
                else:
                    objs = core.list_namespaced_pod(namespace=ns).items
                    ac = client.ApiClient()
                    items = [ac.sanitize_for_serialization(o) for o in objs]
                    j = {"items": items}
                    j.update(self._time_info())
                    if output_format == "yaml":
                        import yaml
                        j["yaml"] = yaml.safe_dump(items, sort_keys=False)
                    yield self.create_json_message(j)
                    yield self.create_text_message(self._append_time(f"Listed pods count={len(items)}"))
            elif resource_type == "node":
                if name:
                    obj = core.read_node(name=name)
                    ac = client.ApiClient()
                    data = ac.sanitize_for_serialization(obj)
                    j = {}
                    if output_format == "yaml":
                        import yaml
                        j["yaml"] = yaml.safe_dump(data, sort_keys=False)
                    else:
                        j["object"] = data
                    j.update(self._time_info())
                    yield self.create_json_message(j)
                    yield self.create_text_message(self._append_time(f"Fetched node {name} format={output_format}"))
                else:
                    objs = core.list_node().items
                    ac = client.ApiClient()
                    items = [ac.sanitize_for_serialization(o) for o in objs]
                    j = {"items": items}
                    j.update(self._time_info())
                    if output_format == "yaml":
                        import yaml
                        j["yaml"] = yaml.safe_dump(items, sort_keys=False)
                    yield self.create_json_message(j)
                    yield self.create_text_message(self._append_time(f"Listed nodes count={len(items)}"))
            else:
                yield self.create_text_message(self._append_time("Error: unsupported resourceType"))
                return
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