## k8s-updater

**Author:** bond-zhu
**Version:** 0.0.1
**Type:** tool

### Description

- 通过 Dify 插件操作 Kubernetes 集群
- 新增工具 `k8s-list`：上传 `kubeconfig` 后列出 Deployment 与 Pod（可按命名空间过滤）

### 使用方法

- 在插件面板选择工具 `k8s-list`
- 上传目标集群的 `kubeconfig` 文件
- 可选填写 `namespace`，为空则列出所有命名空间
- 返回 JSON：`deployments` 与 `pods` 列表以及数量摘要



