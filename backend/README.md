# Athena Reports

Sistema local para geração de relatórios em PDF com base em dados do Zabbix, com suporte a múltiplos hosts, múltiplos gráficos, e estrutura visual padronizada com logo, capa, sumário, cabeçalho e rodapé.

---

## ✅ Funcionalidades já implementadas

- 🔐 Autenticação compatível com Zabbix 7.0 e 7.2 (via API e Web).
- 📊 Listagem de Hostgroups, Hosts e Gráficos.
- 🧾 Geração de relatórios PDF:
  - Capa com logo personalizado
  - Sumário por Host > Gráficos
  - Imagens de gráficos capturados via Web
  - Cabeçalho e rodapé em todas as páginas
  - Período do relatório destacado
- 🖼️ Suporte a logo customizado (`app/static/logo.png`)
- 📂 Armazenamento em `reports/` com nome baseado no hostgroup
- 📜 Logs em `logs/athena.log`
- 🔧 Configurações por `.env`

---

## 📁 Estrutura de diretórios
```
athena-reports/
├── app/
│   ├── core/              # Configurações e logging
│   ├── reports/           # Rotas e serviço de relatório
│   ├── static/            # Logo personalizado
│   ├── zabbix/            # Integração com API e Web Zabbix
│   └── main.py            # Entrypoint FastAPI
├── logs/                  # Arquivos de log
├── reports/               # PDFs gerados
├── .env                   # Variáveis de ambiente
├── README.md              # Documentação
└── requirements.txt       # Dependências Python
```

---

## 📦 Exemplo de payload para gerar relatório
```json
{
  "hostgroup": {
    "id": "32",
    "name": "Cliente/Catupiry"
  },
  "hosts": [
    {
      "id": "10532",
      "name": "Catupiry - CD",
      "graphs": [
        {
          "id": "3196",
          "name": "Tráfego - X4 (WAN)",
          "from_time": "2025-06-20 00:00:00",
          "to_time": "2025-07-01 00:00:00"
        },
        {
          "id": "8924",
          "name": "Tráfego - X5 (WAN)",
          "from_time": "2025-06-20 00:00:00",
          "to_time": "2025-07-01 00:00:00"
        }
      ]
    }
  ]
}
```

---

## 🚀 Como executar
1. Crie e ative um ambiente virtual:
```bash
python3 -m venv venv
source venv/bin/activate
```
2. Instale as dependências:
```bash
pip install -r requirements.txt
```
3. Configure o `.env` com as credenciais do Zabbix:
```
ZABBIX_API_URL=https://monitor.athenasecurity.com.br/api_jsonrpc.php
ZABBIX_WEB_URL=https://monitor.athenasecurity.com.br
ZABBIX_USER=seu_usuario
ZABBIX_PASS=sua_senha
```
4. Execute o servidor:
```bash
uvicorn app.main:app --reload
```

---

## 📌 Próximos passos sugeridos
- Agendador local para geração automática de relatórios
- Interface local com Streamlit ou FastAPI com Jinja2
- Histórico e controle de relatórios gerados
- Envio de relatórios por e-mail
- Customização por cliente (logo, remetente, temas)

---

Para dúvidas ou melhorias, entre em contato com o responsável pelo projeto.

---

© Athena Reports
