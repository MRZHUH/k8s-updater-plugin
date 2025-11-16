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
            if not resource_type or not name:
                yield self.create_text_message(self._append_time("Error: resourceType and name are required"))
                return
            ns = namespace or "default"
            apps = client.AppsV1Api(api_client)
            core = client.CoreV1Api(api_client)
            net = client.NetworkingV1Api(api_client)
            if resource_type == "deployment":
                obj = apps.read_namespaced_deployment(name=name, namespace=ns)
            elif resource_type == "statefulset":
                obj = apps.read_namespaced_stateful_set(name=name, namespace=ns)
            elif resource_type == "daemonset":
                obj = apps.read_namespaced_daemon_set(name=name, namespace=ns)
            elif resource_type == "service":
                obj = core.read_namespaced_service(name=name, namespace=ns)
            elif resource_type == "ingress":
                obj = net.read_namespaced_ingress(name=name, namespace=ns)
            elif resource_type == "pod":
                obj = core.read_namespaced_pod(name=name, namespace=ns)
            else:
                yield self.create_text_message(self._append_time("Error: unsupported resourceType"))
                return
            ac = client.ApiClient()
            data = ac.sanitize_for_serialization(obj)
            j = {}
            if output_format == "yaml":
                import yaml
                y = yaml.safe_dump(data, sort_keys=False)
                j["yaml"] = y
            else:
                j["object"] = data
            j.update(self._time_info())
            yield self.create_json_message(j)
            yield self.create_text_message(self._append_time(f"Fetched {resource_type} {name} in namespace {ns} format={output_format}"))
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
                return client.ApiClient(), {"source": "path"}
            if "file" in kubeconfig_param and isinstance(kubeconfig_param["file"], dict):
                p = kubeconfig_param["file"].get("path")
                if isinstance(p, str) and os.path.exists(p):
                    config.load_kube_config(config_file=p)
                    return client.ApiClient(), {"source": "file.path"}
            if "content" in kubeconfig_param and isinstance(kubeconfig_param["content"], str):
                raw = kubeconfig_param["content"].strip()
                decoded = base64.b64decode(raw).decode("utf-8")
                data = yaml.safe_load(decoded)
                config.load_kube_config_from_dict(data)
                return client.ApiClient(), {"source": "content-base64"}
        if isinstance(kubeconfig_param, str):
            s = kubeconfig_param.strip()
            if os.path.exists(s):
                config.load_kube_config(config_file=s)
                return client.ApiClient(), {"source": "str.path"}
            decoded = base64.b64decode(s).decode("utf-8")
            data = yaml.safe_load(decoded)
            config.load_kube_config_from_dict(data)
            return client.ApiClient(), {"source": "str.base64"}
        raise ValueError("Invalid kubeconfig")

    def _time_info(self) -> dict[str, str]:
        import datetime
        dt = datetime.datetime.now(datetime.timezone.utc).astimezone()
        tz = dt.tzname() or "local"
        return {"timezone": tz, "time": dt.isoformat()}

    def _append_time(self, text: str) -> str:
        info = self._time_info()
        return f"{text} | timezone={info['timezone']} time={info['time']}"