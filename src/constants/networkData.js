async function loadRealData() {
    console.log("Buscando dados no MikroTik...");

    const btn = document.querySelector(
        'button[onclick="loadRealData()"]'
    );

    if (btn) btn.innerText = "⌛ Aguarde...";

    try {

        const response = await fetch(
            'http://localhost:8000/api/network-status'
        );

        const data = await response.json();

        // TRATA ERRO DA API
        if (data.error) {
            console.error("Erro API:", data.error);

            alert("Erro no backend:\n" + data.error);

            return;
        }

        // Sincroniza dados
        for (let key in data) {
            NETWORK_DATA[key] = data[key];
        }

        // Render
        renderRouterInfo(data.router);
        renderVpn(data.vpn);
        renderVlanCards(data.vlans);
        renderDevicesTable(data.devices);
        renderTopStats(data);

        updateTime();

        // Charts
        if (data.vlans) {

            data.vlans.forEach(v => {

                if (!charts[v.id]) {
                    buildVlanChart(v);

                } else {

                    updateChartsWithRealData(
                        v.id,
                        v.rx,
                        v.tx
                    );
                }
            });
        }

        // Logs
        if (data.logs) {
            renderRealLogs(data.logs);
        }

        console.log("Dashboard sincronizado!");

    } catch (error) {

        console.error(
            "Erro na sincronização:",
            error
        );

        alert(
            "Falha ao conectar no backend.\n" +
            "Verifique se o FastAPI está rodando."
        );

    } finally {

        if (btn) {
            btn.innerText = "↻ Atualizar";
        }
    }
}

function renderVpn(vpn) {

    const online = vpn.status === 'online';

    document.getElementById('vpnBadge').className =
        online
            ? 'badge-online'
            : 'badge-offline';

    document.getElementById('vpnBadge').textContent =
        online
            ? '● Online'
            : '○ Offline';

    document.getElementById('vpnIp').textContent =
        vpn.tunnelIp || '—';

    document.getElementById('vpnEndpoint').textContent =
        vpn.endpoint || 'N/A';

    document.getElementById('vpnHandshake').textContent =
        vpn.lastHandshake
            ? `${vpn.lastHandshake}s atrás`
            : 'Sem handshake';

    document.getElementById('vpnPeers').textContent =
        vpn.peers != null
            ? `${vpn.peers} peer(s)`
            : '—';

    document.getElementById('vpnRx').textContent =
        vpn.rxBytes || '—';

    document.getElementById('vpnTx').textContent =
        vpn.txBytes || '—';
}