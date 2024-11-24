import kopf
import kubernetes
import time
from kubernetes import client, config

# Load kubeconfig (or use in-cluster config if running inside a pod)
config.load_kube_config()

# The string you want to monitor in the pod logs
TARGET_STRING = "kill"

# The time interval to check logs (in seconds)
LOG_CHECK_INTERVAL = 10  # Adjust as needed

# Function to check logs and delete pod if TARGET_STRING is found
def check_pod_logs(namespace, pod_name, logger):
    try:
        # Get the logs of the pod
        api_instance = kubernetes.client.CoreV1Api()
        pod_logs = api_instance.read_namespaced_pod_log(name=pod_name, namespace=namespace)

        logger.info(f"Checking logs for pod {pod_name}...")

        # Check if the target string is in the logs
        if TARGET_STRING in pod_logs:
            logger.warning(f"Found target string '{TARGET_STRING}' in pod logs. Deleting pod {pod_name}.")
            
            # Delete the pod if the string is found
            api_instance.delete_namespaced_pod(name=pod_name, namespace=namespace)
            logger.info(f"Pod {pod_name} deleted successfully.")
        else:
            logger.info(f"Target string '{TARGET_STRING}' not found in pod logs.")
    except Exception as e:
        logger.error(f"Error checking logs for pod {pod_name}: {e}")

# Operator handler that runs when a Pod is created or updated
@kopf.on.create('apps', 'v1', 'pods')
@kopf.on.update('apps', 'v1', 'pods')
def pod_created_or_updated(spec, name, namespace, logger, **kwargs):
    logger.info(f"Pod {name} created or updated. Monitoring logs...")

    # Continuously check the pod's logs at intervals
    while True:
        check_pod_logs(namespace, name, logger)
        time.sleep(LOG_CHECK_INTERVAL)  # Wait for a specified interval before checking again

# You can also handle pod deletion if needed
@kopf.on.delete('apps', 'v1', 'pods')
def pod_deleted(name, namespace, logger, **kwargs):
    logger.info(f"Pod {name} deleted, no longer monitoring logs.")
