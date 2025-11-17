## Privacy

This plugin operates inside your Dify environment and interacts only with your Kubernetes API server as configured by your kubeconfig. We are committed to minimizing data collection and avoiding persistence of sensitive data.

### Data Collected and Usage
- Kubeconfig (base64 content or file path): used only at runtime to establish a secure connection to your cluster. The plugin does not store kubeconfig contents on disk or transmit them to third parties.
- Tool parameters (e.g., resource type, name, namespace, image/tag, env keys/values): used to perform requested Kubernetes API calls. These parameters are not persisted by the plugin.
- Outputs: resource metadata and status are returned to you. Some non‑secret metadata (e.g., context/cluster name, server endpoint) may be included to aid debugging and traceability.

### Logging
- The plugin avoids logging secrets (client keys/certificates or raw kubeconfig content). Diagnostic logs may include types and lengths, and may show non‑secret metadata such as cluster/server/namespace.

### Storage and Retention
- The plugin itself does not persist credentials or Kubernetes data to local storage.
- If you configure credentials in the Dify platform, storage and retention are governed by the platform’s settings and policies.

### Network and Security
- Network calls are limited to the Kubernetes API server defined in your kubeconfig.
- TLS behavior follows your configuration (`tlsMode` or kubeconfig settings). We recommend strict verification in production.

### Your Controls
- You may remove credentials and disable the plugin at any time via the platform.
- For issues or requests, please contact the maintainer.
