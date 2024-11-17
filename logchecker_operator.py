import kopf
import kubernetes
from kubernetes import client, config
import threading
import time

# Load kube config
config.load_incluster_config()

# Dictionary to hold active log tailing threads
active_threads = {}

@kopf.on.create('LogChecker')
@kopf.on.update('LogChecker')
def create_or_update_fn(spec, name, namespace, **kwargs):
    deployment_name = spec.get('deploymentName')
    search_string = spec.get('searchString')

    # Stop and remove any existing thread for this LogChecker
    if name in active_threads:
        active_threads[name]['stop_event'].set()
        active_threads[name]['thread'].join()

    # Create a new stop event for the new thread
    stop_event = threading.Event()
    
    def tail_logs(stop_event):
        v1 = client.CoreV1Api()
        while not stop_event.is_set():
            try:
                pod_list = v1.list_namespaced_pod(namespace, label_selector=f'app={deployment_name}')
                
                for pod in pod_list.items:
                    pod_name = pod.metadata.name
                    pod_log = v1.read_namespaced_pod_log(name=pod_name, namespace=namespace, follow=True, _preload_content=False)
                    
                    for line in pod_log:
                        if stop_event.is_set():
                            break
                        line = line.decode('utf-8').strip()
                        if search_string in line:
                            print(f"Found '{search_string}' in pod {pod_name} log line: {line}")
                            delete_pod(namespace, pod_name)
                            return  # Exit after restarting the pod
            except Exception as e:
                print(f"Error fetching pod logs: {e}")
                time.sleep(10)  # Retry after a delay

    # Start a new thread for log tailing
    thread = threading.Thread(target=tail_logs, args=(stop_event,))
    thread.start()
    
    # Store the thread and stop event in the active_threads dictionary
    active_threads[name] = {'thread': thread, 'stop_event': stop_event}

@kopf.on.delete('LogChecker')
def delete_fn(name, **kwargs):
    # Stop and remove the thread for this LogChecker
    if name in active_threads:
        active_threads[name]['stop_event'].set()
        active_threads[name]['thread'].join()
        del active_threads[name]

def delete_pod(namespace, pod_name):
    v1 = client.CoreV1Api()
    try:
        v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        print(f"Pod {pod_name} in namespace {namespace} has been deleted and will be restarted.")
    except Exception as e:
        print(f"Error deleting pod {pod_name}: {e}")
