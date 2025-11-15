from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

class K8sListTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        namespace = tool_parameters.get("namespace")
        kubeconfig_param = self.runtime.credentials.get("kubeconfig")
        try:
            api_client = self._build_api_client(kubeconfig_param)
            from kubernetes import client
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
            yield self.create_json_message({"deployments": deployments, "pods": pod_list})
            yield self.create_text_message(f"Deployments: {len(deployments)}, Pods: {len(pod_list)}")
        except Exception as e:
            yield self.create_text_message(f"Error: {str(e)}")

    def _build_api_client(self, kubeconfig_param: Any):
        from kubernetes import client, config
        import yaml
        if isinstance(kubeconfig_param, dict):
            if "path" in kubeconfig_param:
                config.load_kube_config(config_file=kubeconfig_param["path"])
                return client.ApiClient()
            if "content" in kubeconfig_param:
                data = yaml.safe_load(kubeconfig_param["content"])
                try:
                    config.load_kube_config_from_dict(data)
                except Exception:
                    config.load_kube_config_from_dict(data)
                return client.ApiClient()
            if "file" in kubeconfig_param and isinstance(kubeconfig_param["file"], dict) and "path" in kubeconfig_param["file"]:
                config.load_kube_config(config_file=kubeconfig_param["file"]["path"])
                return client.ApiClient()
        if isinstance(kubeconfig_param, str):
            try:
                data = yaml.safe_load(kubeconfig_param)
                config.load_kube_config_from_dict(data)
                return client.ApiClient()
            except Exception:
                config.load_kube_config(config_file=kubeconfig_param)
                return client.ApiClient()
        raise ValueError("Invalid kubeconfig parameter")