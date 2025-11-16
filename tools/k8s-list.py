from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

class K8sListTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        namespace = tool_parameters.get("namespace")
        kubeconfig_param = self.runtime.credentials.get("kubeconfig")
        try:
            info = self._debug_cred_info(kubeconfig_param)
            yield self.create_text_message(self._append_time(f"kubeconfig credential: {info}"))
        except Exception as _:
            pass
        try:
            api_client, src_info = self._build_api_client(kubeconfig_param)
            from kubernetes import client
            try:
                yield self.create_text_message(self._append_time(f"kubeconfig source: {src_info}"))
            except Exception as _:
                pass
            try:
                from kubernetes.client.rest import ApiException
                core_v1_probe = client.CoreV1Api(api_client)
                _ = core_v1_probe.list_namespace(limit=1)
                yield self.create_text_message(self._append_time("k8s connectivity: ok"))
            except Exception as e:
                try:
                    from kubernetes.client.rest import ApiException
                    if isinstance(e, ApiException):
                        yield self.create_text_message(self._append_time(f"k8s connectivity error: status={e.status} reason={e.reason}"))
                        try:
                            body = (e.body or "")
                            if isinstance(body, str):
                                yield self.create_text_message(self._append_time(body[:500]))
                        except Exception:
                            pass
                        return
                except Exception:
                    pass
                yield self.create_text_message(self._append_time(f"k8s connectivity error: {str(e)}"))
                return
            apps_v1 = client.AppsV1Api(api_client)
            core_v1 = client.CoreV1Api(api_client)
            if namespace:
                dps = apps_v1.list_namespaced_deployment(namespace=namespace).items
                pods = core_v1.list_namespaced_pod(namespace=namespace).items
            else:
                dps = apps_v1.list_deployment_for_all_namespaces().items
                pods = core_v1.list_pod_for_all_namespaces().items
            deployments = []
            for d in dps:
                images = [c.image for c in (d.spec.template.spec.containers or [])]
                deployments.append({
                    "name": d.metadata.name,
                    "namespace": d.metadata.namespace,
                    "labels": d.metadata.labels or {},
                    "replicas": d.spec.replicas,
                    "availableReplicas": d.status.available_replicas or 0,
                    "images": images,
                })
            pod_list = []
            for p in pods:
                images = [c.image for c in (p.spec.containers or [])]
                pod_list.append({
                    "name": p.metadata.name,
                    "namespace": p.metadata.namespace,
                    "phase": p.status.phase,
                    "nodeName": p.spec.node_name,
                    "podIP": p.status.pod_ip,
                    "images": images,
                })
            j = {"deployments": deployments, "pods": pod_list}
            j.update(self._time_info())
            yield self.create_json_message(j)
            yield self.create_text_message(self._append_time(f"Deployments: {len(deployments)}, Pods: {len(pod_list)}"))
        except Exception as e:
            yield self.create_text_message(self._append_time(f"Error: {str(e)}"))

    def _build_api_client(self, kubeconfig_param: Any):
        from kubernetes import client, config
        import yaml
        import os
        import base64
        try:
            print(f"kubeconfig type: {type(kubeconfig_param).__name__}")
        except Exception as _:
            pass

        def _extract_info_from_data(data: Any, source: str):
            try:
                ctx_name = data.get("current-context")
                cluster_name = None
                server = None
                user_name = None
                try:
                    contexts = data.get("contexts") or []
                    for c in contexts:
                        if isinstance(c, dict):
                            n = c.get("name")
                            if (not ctx_name) and n:
                                ctx_name = n
                            if ctx_name and n == ctx_name:
                                u = c.get("context") or {}
                                cluster_name = u.get("cluster")
                                user_name = u.get("user")
                                break
                except Exception:
                    pass
                try:
                    clusters = data.get("clusters") or []
                    for c in clusters:
                        if isinstance(c, dict):
                            n = c.get("name")
                            if cluster_name and n != cluster_name:
                                continue
                            ci = c.get("cluster") or {}
                            if isinstance(ci, dict):
                                server = ci.get("server")
                                if cluster_name is None:
                                    cluster_name = n
                                if server:
                                    break
                except Exception:
                    pass
                return {
                    "source": source,
                    "context": ctx_name,
                    "cluster": cluster_name,
                    "server": server,
                    "user": user_name,
                }
            except Exception:
                return {"source": source}

        def _load_from_dict(data: Any, source: str):
            if not isinstance(data, dict):
                raise ValueError("Invalid kubeconfig content")
            contexts = data.get("contexts") or []
            if "current-context" not in data and isinstance(contexts, list) and contexts:
                first = contexts[0]
                name = first.get("name") if isinstance(first, dict) else None
                if name:
                    data["current-context"] = name
            info = _extract_info_from_data(data, source)
            config.load_kube_config_from_dict(data)
            return client.ApiClient(), info

        if isinstance(kubeconfig_param, dict):
            if "path" in kubeconfig_param and isinstance(kubeconfig_param["path"], str) and os.path.exists(kubeconfig_param["path"]):
                try:
                    print(f"loading kubeconfig from path: {kubeconfig_param['path']}")
                except Exception as _:
                    pass
                config.load_kube_config(config_file=kubeconfig_param["path"])
                info = {}
                try:
                    with open(kubeconfig_param["path"], "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f.read())
                        if isinstance(data, dict):
                            info = _extract_info_from_data(data, "path")
                except Exception:
                    info = {"source": "path"}
                return client.ApiClient(), info
            if "file" in kubeconfig_param and isinstance(kubeconfig_param["file"], dict):
                p = kubeconfig_param["file"].get("path")
                if isinstance(p, str) and os.path.exists(p):
                    try:
                        print(f"loading kubeconfig from file.path: {p}")
                    except Exception as _:
                        pass
                    config.load_kube_config(config_file=p)
                    info = {}
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            data = yaml.safe_load(f.read())
                            if isinstance(data, dict):
                                info = _extract_info_from_data(data, "file.path")
                    except Exception:
                        info = {"source": "file.path"}
                    return client.ApiClient(), info
            if "content" in kubeconfig_param and isinstance(kubeconfig_param["content"], str):
                raw = kubeconfig_param["content"].strip()
                try:
                    print(f"loading kubeconfig from base64 content len: {len(raw)}")
                except Exception as _:
                    pass
                try:
                    decoded = base64.b64decode(raw).decode("utf-8")
                    data = yaml.safe_load(decoded)
                except Exception:
                    raise ValueError("Invalid kubeconfig: expect base64-encoded content")
                return _load_from_dict(data, "content-base64")

        if isinstance(kubeconfig_param, str):
            s = kubeconfig_param.strip()
            try:
                if ("\\n" in s) and ("\n" not in s):
                    before_len = len(s)
                    s2 = None
                    try:
                        s2 = bytes(s, "utf-8").decode("unicode_escape")
                    except Exception:
                        pass
                    if not s2:
                        s2 = s.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "\t")
                    s = s2
                    try:
                        print(f"unescaped kubeconfig string: {before_len} -> {len(s)}")
                    except Exception:
                        pass
            except Exception:
                pass
            if os.path.exists(s):
                try:
                    print(f"loading kubeconfig from str path: {s}")
                except Exception as _:
                    pass
                config.load_kube_config(config_file=s)
                info = {}
                try:
                    with open(s, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f.read())
                        if isinstance(data, dict):
                            info = _extract_info_from_data(data, "str.path")
                except Exception:
                    info = {"source": "str.path"}
                return client.ApiClient(), info
            try:
                try:
                    print(f"loading kubeconfig from str base64 len: {len(s)}")
                except Exception as _:
                    pass
                decoded = base64.b64decode(s).decode("utf-8")
                data = yaml.safe_load(decoded)
                return _load_from_dict(data, "str.base64")
            except Exception:
                raise ValueError("Invalid kubeconfig: expect base64 or file path")

        env_path = os.environ.get("KUBECONFIG") or os.path.join(os.path.expanduser("~"), ".kube", "config")
        if isinstance(env_path, str) and os.path.exists(env_path):
            try:
                print(f"loading kubeconfig from env/default path: {env_path}")
            except Exception as _:
                pass
            config.load_kube_config(config_file=env_path)
            info = {}
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f.read())
                    if isinstance(data, dict):
                        info = _extract_info_from_data(data, "env.path")
            except Exception:
                info = {"source": "env.path"}
            return client.ApiClient(), info

        raise ValueError("Invalid kubeconfig: please upload file or provide valid path")

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


    def _parse_singleline_kubeconfig(self, s: str) -> Any:
        import re
        try:
            api = "v1" if "apiVersion:" in s else None
            server = None
            ca = None
            cert = None
            key = None
            ctx = None
            ns = None
            cluster_name = None
            user_name = None

            m = re.search(r"server:\s*(\S+)", s)
            if m:
                server = m.group(1)
            m = re.search(r"certificate-authority-data:\s*([A-Za-z0-9+/=]+)", s)
            if m:
                ca = m.group(1)
            m = re.search(r"client-certificate-data:\s*([A-Za-z0-9+/=]+)", s)
            if m:
                cert = m.group(1)
            m = re.search(r"client-key-data:\s*([A-Za-z0-9+/=]+)", s)
            if m:
                key = m.group(1)
            m = re.search(r"current-context:\s*(\S+)", s)
            if m:
                ctx = m.group(1)
            m = re.search(r"namespace:\s*(\S+)", s)
            if m:
                ns = m.group(1)
            # try to pick names near cluster/user
            m = re.search(r"clusters?:.*?name:\s*(\S+)", s)
            if m:
                cluster_name = m.group(1)
            m = re.search(r"users?:.*?name:\s*(\S+)", s)
            if m:
                user_name = m.group(1)

            if not server:
                return None

            data = {
                "apiVersion": api or "v1",
                "kind": "Config",
                "clusters": [
                    {
                        "name": cluster_name or "cluster",
                        "cluster": {
                            "server": server,
                        },
                    }
                ],
                "users": [
                    {
                        "name": user_name or "user",
                        "user": {},
                    }
                ],
                "contexts": [
                    {
                        "name": ctx or (cluster_name or "cluster"),
                        "context": {
                            "cluster": cluster_name or "cluster",
                            "user": user_name or "user",
                        },
                    }
                ],
                "current-context": ctx or (cluster_name or "cluster"),
            }
            if ns:
                try:
                    data["contexts"][0]["context"]["namespace"] = ns
                except Exception:
                    pass
            if ca:
                try:
                    data["clusters"][0]["cluster"]["certificate-authority-data"] = ca
                except Exception:
                    pass
            if cert:
                try:
                    data["users"][0]["user"]["client-certificate-data"] = cert
                except Exception:
                    pass
            if key:
                try:
                    data["users"][0]["user"]["client-key-data"] = key
                except Exception:
                    pass
            return data
        except Exception:
            return None

    def _time_info(self) -> dict[str, str]:
        import datetime
        dt = datetime.datetime.now(datetime.timezone.utc).astimezone()
        tz = dt.tzname() or "local"
        return {"timezone": tz, "time": dt.isoformat()}

    def _append_time(self, text: str) -> str:
        info = self._time_info()
        return f"{text} | timezone={info['timezone']} time={info['time']}"