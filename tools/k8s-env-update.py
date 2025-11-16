from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

class K8sEnvUpdateTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        resource_type = (tool_parameters.get("resourceType") or "").strip().lower()
        alias = {
            "deploy": "deployment",
            "deployment": "deployment",
            "sts": "statefulset",
            "statefulset": "statefulset",
            "ds": "daemonset",
            "daemonset": "daemonset",
        }
        resource_type = alias.get(resource_type, resource_type)
        name = (tool_parameters.get("name") or "").strip()
        namespace = (tool_parameters.get("namespace") or "").strip() or None
        env_key = (tool_parameters.get("envKey") or "").strip()
        env_value = (tool_parameters.get("envValue") or "").strip()
        container_filter = (tool_parameters.get("container") or "").strip() or None
        kubeconfig_param = self.runtime.credentials.get("kubeconfig")
        try:
            api_client, _ = self._build_api_client(kubeconfig_param)
            from kubernetes import client
            apps = client.AppsV1Api(api_client)
            if resource_type not in {"deployment", "statefulset", "daemonset"}:
                yield self.create_text_message(self._append_time("Error: invalid resourceType"))
                return
            if not name or not env_key:
                yield self.create_text_message(self._append_time("Error: name and envKey are required"))
                return
            ns = namespace or "default"
            getter = {
                "deployment": apps.read_namespaced_deployment,
                "statefulset": apps.read_namespaced_stateful_set,
                "daemonset": apps.read_namespaced_daemon_set,
            }[resource_type]
            patcher = {
                "deployment": apps.patch_namespaced_deployment,
                "statefulset": apps.patch_namespaced_stateful_set,
                "daemonset": apps.patch_namespaced_daemon_set,
            }[resource_type]
            obj = getter(name=name, namespace=ns)
            containers = list((obj.spec.template.spec.containers or []))
            changed = []
            unchanged = []
            patch_containers = []
            for c in containers:
                if container_filter and c.name != container_filter:
                    continue
                cur_env = list(c.env or [])
                found = False
                cur_val = None
                for e in cur_env:
                    if e.name == env_key:
                        found = True
                        cur_val = e.value
                        break
                if found:
                    if str(cur_val or "") == env_value:
                        unchanged.append({"container": c.name, "key": env_key, "value": cur_val})
                    else:
                        changed.append({"container": c.name, "key": env_key, "from": cur_val, "to": env_value})
                        new_env = []
                        for e in cur_env:
                            if e.name == env_key:
                                new_env.append({"name": env_key, "value": env_value})
                            else:
                                new_env.append({"name": e.name, "value": e.value})
                        patch_containers.append({"name": c.name, "env": new_env})
                else:
                    changed.append({"container": c.name, "key": env_key, "from": None, "to": env_value})
                    new_env = list({"name": e.name, "value": e.value} for e in cur_env)
                    new_env.append({"name": env_key, "value": env_value})
                    patch_containers.append({"name": c.name, "env": new_env})
            if not changed:
                j = {"changed": changed, "unchanged": unchanged}
                j.update(self._time_info())
                yield self.create_json_message(j)
                yield self.create_text_message(self._append_time("No changes applied"))
                return
            body = {"spec": {"template": {"spec": {"containers": patch_containers}}}}
            patcher(name=name, namespace=ns, body=body)
            j = {"changed": changed, "unchanged": unchanged}
            j.update(self._time_info())
            yield self.create_json_message(j)
            yield self.create_text_message(self._append_time(f"Updated {resource_type} {name} in namespace {ns}"))
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