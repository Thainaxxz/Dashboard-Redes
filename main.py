from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routeros_api import RouterOsApiPool
import uvicorn
import time
import threading
import os
from dotenv import load_dotenv


load_dotenv()

app = FastAPI()


HOST = os.getenv('MIKROTIK_HOST')
USER = os.getenv('MIKROTIK_USER')
PASS = os.getenv('MIKROTIK_PASS')


# ─────────────────────────────────────────────
#  Cache de tráfego — atualizado em background
# ─────────────────────────────────────────────
_traffic_cache: dict = {}   # { 'vlan50': {'rx': 0.0, 'tx': 0.0} }
_prev_snapshot: dict = {}   # { 'vlan50': {'rx': bytes, 'tx': bytes, 'time': float} }
_cache_lock = threading.Lock()


def _collect_traffic():
    """Roda em background a cada 10s e calcula Mbps real."""
    while True:
        try:
            pool = RouterOsApiPool(
                HOST,
                username=USER,
                password=PASS,
                plaintext_login=True,
            )
            api  = pool.get_api()
            now  = time.time()

            interfaces = api.get_resource('/interface').get()          
            
            new_cache    = {}
            new_snapshot = {}

            for iface in interfaces:
                name = iface.get('name')
                
                rx_bytes = int(iface.get('rx-byte', 0))
                tx_bytes = int(iface.get('tx-byte', 0))

                prev = _prev_snapshot.get(name)

                if prev and (now - prev['time']) >= 2:
                    elapsed = now - prev['time']
                    rx_mbps = round(((rx_bytes - prev['rx']) * 8) / elapsed / 1_000_000, 2)
                    tx_mbps = round(((tx_bytes - prev['tx']) * 8) / elapsed / 1_000_000, 2)
                    rx_mbps = max(rx_mbps, 0.0)
                    tx_mbps = max(tx_mbps, 0.0)
                else:
                    rx_mbps = 0.0
                    tx_mbps = 0.0

                new_cache[name]    = {'rx': rx_mbps, 'tx': tx_mbps}
                new_snapshot[name] = {'rx': rx_bytes, 'tx': tx_bytes, 'time': now}

            pool.disconnect()

            with _cache_lock:
                _traffic_cache.update(new_cache)
                _prev_snapshot.update(new_snapshot)

        except Exception as e:
            print(f"[TRAFFIC ERROR] {e}")

        time.sleep(10)


# Inicia o coletor em background ao subir o servidor
_collector_thread = threading.Thread(target=_collect_traffic, daemon=True)
_collector_thread.start()


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────
def get_vlan_from_ip(ip: str):
    octets = {
        "10.10.10.": "LAN",
        "10.10.40.": 40,  "10.10.50.": 50,  "10.10.60.": 60,
        "10.10.70.": 70,  "10.10.80.": 80,  "10.10.90.": 90,
        "10.10.100.": 100,"10.10.110.": 110,"10.10.120.": 120,
        "10.10.130.": 130,"10.10.140.": 140,
    }
    for prefix, vlan in octets.items():
        if ip.startswith(prefix):
            return vlan
    return "Desconhecido"


VLAN_COLORS = {
    '10': '#3b82f6', '20': '#8b5cf6', '30': '#f59e0b',
    '40': '#10b981', '50': '#ef4444', 'default': '#8b949e',
}


# ─────────────────────────────────────────────
#  Coleta principal (sem tráfego — só dados)
# ─────────────────────────────────────────────
def get_mikrotik_data():
    pool = None
    try:
        pool = RouterOsApiPool(
            HOST, username=USER, password=PASS, plaintext_login=True,
        )
        api = pool.get_api()

        vlan_resources = api.get_resource('/interface/vlan').get()
        leases         = api.get_resource('/ip/dhcp-server/lease').get()
        resource       = api.get_resource('/system/resource').get()[0]

        # ── VLANs ──────────────────────────────
        vlans_list = []
        with _cache_lock:
            cache_snapshot = dict(_traffic_cache)

        NOME_IFACE_FISICA = 'ether3-lan'  # Ajuste conforme seu modelo
        
        traffic_fisica = cache_snapshot.get(NOME_IFACE_FISICA, {'rx': 0.0, 'tx': 0.0})
        
        # Contar devices da LAN (que começam com 10.10.10.)
        devices_lan = len([l for l in leases if l.get('status') == 'bound' and l.get('address', '').startswith('10.10.10.')])

        vlans_list.append({
            "id":      "LAN",
            "name":    "Rede Física Interna",
            "color":   "#3b82f6", # Azul para destacar
            "rx":      traffic_fisica['rx'],
            "tx":      traffic_fisica['tx'],
            "rxUnit":  "Mbps",
            "txUnit":  "Mbps",
            "devices": devices_lan,
            "status":  "ok",
        })

        for v in vlan_resources:
            v_name = v.get('name')
            v_id   = v.get('vlan-id')

            traffic   = cache_snapshot.get(v_name, {'rx': 0.0, 'tx': 0.0})
            rx_mbps   = traffic['rx']
            tx_mbps   = traffic['tx']

            devices_count = len([
                l for l in leases
                if l.get('status') == 'bound'
                and l.get('server') == f'dhcp_vlan{v_id}'
            ])

            vlans_list.append({
                "id":      int(v_id),
                "name":    v_name,
                "color":   VLAN_COLORS.get(v_id, VLAN_COLORS['default']),
                "rx":      rx_mbps,
                "tx":      tx_mbps,
                "rxUnit":  "Mbps",
                "txUnit":  "Mbps",
                "devices": devices_count,
                "status":  "ok",
            })

        # ── Logs ───────────────────────────────
        # ── Logs ───────────────────────────────
        try:
            raw_logs    = api.get_resource('/log').get()
            # Pegando os últimos 15 logs ao invés de apenas 5 para dar mais contexto
            latest_logs = raw_logs[-15:] if raw_logs else []
        except Exception as e:
            # Esse print vai aparecer no terminal do Uvicorn se der erro
            print(f"[ERRO AO PUXAR LOGS] {e}") 
            latest_logs = []

        # ── Devices ────────────────────────────
        devices = []
        for l in leases:
            ip = l.get('address', '')
            devices.append({
                "ip":       ip,
                "mac":      l.get('mac-address'),
                "hostname": l.get('host-name', 'Desconhecido'),
                "vlan":     get_vlan_from_ip(ip),
                "status":   "online" if l.get('status') == 'bound' else "offline",
                "lease":    l.get('expires-after', 'N/A'),
            })

        # ── Memória ────────────────────────────
        try:
            free_mem  = int(resource.get('free-memory', 0))
            total_mem = int(resource.get('total-memory', 1))
            memory_usage = 100 - int((free_mem / total_mem) * 100)
        except Exception:
            memory_usage = 0

        return {
            "router": {
                "model":   resource.get('board-name', 'MikroTik'),
                "version": resource.get('version', 'N/A'),
                "cpu":     int(resource.get('cpu-load', 0)),
                "memory":  memory_usage,
                "uptime":  resource.get('uptime', 'N/A'),
                "temp":    45,
            },
            "vlans":   vlans_list,
            "devices": devices,
            "vpn": {
                "status":        "online",
                "endpoint":      "Matriz-SP",
                "tunnelIp":      "172.16.0.1",
                "lastHandshake": 12,
                "peers":         2,
                "rxBytes":       "12.4 MB",
                "txBytes":       "5.7 MB",
            },
            "logs": latest_logs,
        }
    
        

    except Exception as e:
        print("ERRO GERAL:", e)
        return {"error": str(e)}

    finally:
        if pool:
            try:
                pool.disconnect()
            except Exception:
                pass


@app.get("/api/network-status")
async def get_status():
    return get_mikrotik_data()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)