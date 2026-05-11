# MikroTik NMS Dashboard

Um sistema de monitoramento de rede (NMS) em tempo real construído para roteadores MikroTik. Desenvolvido para centralizar a visibilidade da infraestrutura e simplificar a rotina em ambientes de suporte técnico e manutenção de hardware.

## O Problema e a Solução
Em operações dinâmicas de infraestrutura, monitorar a entrada e saída de equipamentos e o consumo de banda diretamente pelo Winbox pode ser engessado. Este projeto resolve isso expondo os dados críticos do roteador em uma interface web leve, responsiva e de fácil leitura, atualizada em tempo real.

## Funcionalidades Principais
- **Monitoramento de Tráfego:** Gráficos em tempo real (Mbps) cobrindo tanto a rede física (LAN) quanto múltiplas VLANs.
- **Gestão de Dispositivos (DHCP):** Tabela dinâmica listando equipamentos conectados na bancada, com IP, MAC, hostname e status online/offline.
- **Status de VPN:** Acompanhamento do túnel principal WireGuard (Peers ativos, IPs e tráfego criptografado).
- **Recursos do Sistema:** Monitoramento de uso de CPU, Memória, Uptime e Temperatura do RouterOS.

## Tecnologias Utilizadas
**Back-end:**
- [Python 3](https://www.python.org/)
- [FastAPI](https://fastapi.tiangolo.com/) (API assíncrona e performática)
- `routeros_api` (Comunicação direta com o MikroTik)
- `python-dotenv` (Gestão segura de variáveis de ambiente)

**Front-end:**
- HTML5, CSS3 (Variáveis de cor inspiradas em temas Dark Mode) e JavaScript puro.
- [Chart.js](https://www.chartjs.org/) (Renderização dos gráficos de tráfego).

## Como executar o projeto

### Pré-requisitos
- Python instalado na máquina.
- Acesso à API habilitado no roteador MikroTik (`IP > Services > api`).

### Instalação
1. Clone o repositório:
   ```bash
   git clone [https://github.com/Thainaxxz/Dashboard-Redes.git](https://github.com/Thainaxxz/Dashboard-Redes.git)

2. Instale as dependências:
   ```Bash
   pip install fastapi uvicorn routeros_api python-dotenv

3. Configure as variáveis de ambiente:
 - Renomeie o arquivo .env.example para .env
 - Insira as credenciais do seu roteador (IP, Usuário e Senha).

4. Inicie o servidor Back-end:
 - uvicorn main:app --reload

5. Abra o arquivo index.html diretamente no seu navegador. O dashboard já começará a sincronizar os dados a cada 5 segundos