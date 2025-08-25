import time
import json
import os
import requests
import urllib3
from threading import Thread
from core.keys_loader import load_keys  # noqa: F401
from core.event_bus import event_bus
from core.config import MITCH_ROOT
from core.peterjones import get_logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = get_logger("proxmon")

class ProxMonModule:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.running = True
        self.proxmox_url = "https://192.168.4.210:8006/api2/json"
        self.username = "root@pam"
        self.password = os.getenv("PROXMOX_PASSWORD")
        self.session = requests.Session()
        self.session.verify = False
        self.csrf_token = None
        self.ticket = None

        log_dir = os.path.join(MITCH_ROOT, "data")
        os.makedirs(log_dir, exist_ok=True)
        self.node_log_path = os.path.join(log_dir, "node_status.jsonl")
        self.vm_log_path = os.path.join(log_dir, "vm_status.jsonl")

    def authenticate(self):
        auth_payload = {"username": self.username, "password": self.password}
        response = self.session.post(f"{self.proxmox_url}/access/ticket", data=auth_payload)
        if response.status_code == 200:
            data = response.json()
            self.ticket = data['data']['ticket']
            self.csrf_token = data['data']['CSRFPreventionToken']
            self.session.cookies.set('PVEAuthCookie', self.ticket)
            self.session.headers.update({'CSRFPreventionToken': self.csrf_token})
            logger.debug("Authenticated with Proxmox.")
        else:
            logger.error(f"Proxmox authentication failed: {response.text}")
            raise Exception("Proxmox authentication failed.")

    def get_nodes(self):
        response = self.session.get(f"{self.proxmox_url}/nodes")
        if response.status_code == 200:
            nodes = [node['node'] for node in response.json().get('data', [])]
            logger.debug(f"Retrieved node list: {nodes}")
            return nodes
        else:
            logger.error(f"Failed to fetch node list: {response.text}")
            return []

    def fetch_node_status(self, node):
        response = self.session.get(f"{self.proxmox_url}/nodes/{node}/status")
        if response.status_code == 200:
            return response.json().get('data', {})
        else:
            logger.error(f"Failed to fetch node status for {node}: {response.text}")
            return {}

    def fetch_vm_list(self, node):
        response = self.session.get(f"{self.proxmox_url}/nodes/{node}/qemu")
        if response.status_code == 200:
            return response.json().get('data', [])
        else:
            logger.error(f"Failed to fetch VM list for {node}: {response.text}")
            return []

    def fetch_vm_status(self, node, vmid):
        response = self.session.get(f"{self.proxmox_url}/nodes/{node}/qemu/{vmid}/status/current")
        if response.status_code == 200:
            return response.json().get('data', {})
        else:
            logger.error(f"Failed to fetch status for VM {vmid} on {node}: {response.text}")
            return {}

    def log_jsonl(self, filepath, record):
        with open(filepath, "a") as f:
            f.write(json.dumps(record) + "\n")

    def run(self):
        logger.info("ProxMon module starting polling loop.")
        while self.running:
            try:
                self.authenticate()

                nodes = self.get_nodes()
                timestamp = time.time()

                for node in nodes:
                    node_status = self.fetch_node_status(node)
                    if node_status:
                        node_record = {"timestamp": timestamp, "node": node, "status": node_status}
                        self.log_jsonl(self.node_log_path, node_record)
                        logger.debug(f"Logged node status for {node}")

                    vms = self.fetch_vm_list(node)
                    for vm in vms:
                        vmid = vm.get('vmid')
                        if vmid:
                            vm_status = self.fetch_vm_status(node, vmid)
                            if vm_status:
                                vm_record = {
                                    "timestamp": timestamp,
                                    "node": node,
                                    "vmid": vmid,
                                    "vm_name": vm.get('name'),
                                    "status": vm_status
                                }
                                self.log_jsonl(self.vm_log_path, vm_record)
                                logger.debug(f"Logged VM {vmid} status on {node}")

            except Exception as e:
                logger.error(f"Error during ProxMon polling cycle: {e}")

            time.sleep(60)

    def shutdown(self):
        logger.info("Shutting down ProxMon Module...")
        self.running = False

    def restart_vm(self, vmid):
        try:
            self.authenticate()
            logger.info(f"Sending restart command for VM {vmid}")
            response = self.session.post(f"{self.proxmox_url}/nodes/mcgregor/qemu/{vmid}/status/reset")
            if response.status_code == 200:
                logger.info(f"VM {vmid} restart initiated.")
                return f"VM {vmid} restart initiated successfully."
            else:
                logger.error(f"Failed to restart VM {vmid}: {response.text}")
                return f"Failed to restart VM {vmid}: {response.text}"
        except Exception as e:
            logger.error(f"Error restarting VM {vmid}: {e}")
            return str(e)

    def get_vm_status(self, vmid):
        try:
            self.authenticate()
            nodes = self.get_nodes()

            for node in nodes:
                vm_list = self.fetch_vm_list(node)
                for vm in vm_list:
                    if vm.get('vmid') == vmid:
                        return self.fetch_vm_status(node, vmid)

            logger.warning(f"VM {vmid} not found.")
            return f"VM {vmid} not found."
        except Exception as e:
            logger.error(f"Error fetching VM status: {e}")
            return str(e)

# Event handling
def handle_restart_vm(event):
    vmid = event.get("vmid")
    if vmid is not None:
        result = proxmon.restart_vm(vmid)
        event_bus.emit("speak", result)

def handle_get_vm_status(event):
    vmid = event.get("vmid")
    if vmid is not None:
        result = proxmon.get_vm_status(vmid)
        event_bus.emit("speak", str(result))

proxmon = ProxMonModule(event_bus)
event_bus.subscribe("restart_vm", handle_restart_vm)
event_bus.subscribe("get_vm_status", handle_get_vm_status)
