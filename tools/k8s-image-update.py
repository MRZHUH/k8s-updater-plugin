from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

class K8sImageUpdateTool(Tool):
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
        image_param = tool_parameters.get("image")
        tag_param = tool_parameters.get("tag")
        container_filter = (tool_parameters.get("container") or "").strip() or None
        kubeconfig_param = self.runtime.credentials.get("kubeconfig")
        try:
            api_client, _ = self._build_api_client(kubeconfig_param)
            from kubernetes import client
            apps = client.AppsV1Api(api_client)
            if resource_type not in {"deployment", "statefulset", "daemonset"}:
                yield self.create_text_message("Error: invalid resourceType")
                return
            if not name:
                yield self.create_text_message("Error: name is required")
                return
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
            ns = namespace or "default"
            obj = getter(name=name, namespace=ns)
            containers = list((obj.spec.template.spec.containers or []))
            desired_repo, desired_tag = self._desired(image_param, tag_param)
            changed = []
            unchanged = []
            patch_containers = []
            for c in containers:
                if container_filter and c.name != container_filter:
                    continue
                cur_repo, cur_tag = self._split_image(c.image or "")
                new_repo = cur_repo if desired_repo is None else desired_repo
                new_tag = cur_tag if desired_tag is None else desired_tag
                if image_param and (":" in str(image_param)) and (tag_param is None):
                    r2, t2 = self._split_image(str(image_param))
                    new_repo = r2
                    new_tag = t2 if t2 else (cur_tag or "latest")
                if desired_repo is None and desired_tag is None:
                    unchanged.append({"container": c.name, "image": c.image})
                    continue
                new_image = new_repo + (f":{new_tag}" if new_tag else "")
                if new_image == (c.image or ""):
                    unchanged.append({"container": c.name, "image": c.image})
                else:
                    changed.append({"container": c.name, "from": c.image, "to": new_image})
                    patch_containers.append({"name": c.name, "image": new_image})
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

    def _split_image(self, img: str) -> tuple[str, str | None]:
        s = img or ""
        ls = s.rfind("/")
        lc = s.rfind(":")
        if lc > ls:
            return s[:lc], s[lc+1:]
        return s, None

    def _desired(self, image_param: Any, tag_param: Any) -> tuple[str | None, str | None]:
        image = (str(image_param) if image_param else None)
        tag = (str(tag_param) if tag_param else None)
        if image and tag:
            r, _t = self._split_image(image)
            return r, tag
        if image and not tag:
            r, t = self._split_image(image)
            return r, t
        if (not image) and tag:
            return None, tag
        return None, None

    def _time_info(self) -> dict[str, str]:
        import datetime
        dt = datetime.datetime.now(datetime.timezone.utc).astimezone()
        tz = dt.tzname() or "local"
        return {"timezone": tz, "time": dt.isoformat()}

    def _append_time(self, text: str) -> str:
        info = self._time_info()
        return f"{text} | timezone={info['timezone']} time={info['time']}"