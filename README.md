# EPG Sync Manager

Ferramenta para corrigir o offset de tempo dos canais no teu EPG (XMLTV).

## Como funciona

- Vai buscar o EPG original automaticamente de 6 em 6 horas
- Aplica o offset que definiste a cada canal
- Serve o XML corrigido num URL que usas no teu player

---

## Deploy no Render.com (passo a passo)

### 1. Criar conta no GitHub
- Vai a https://github.com e cria conta gratuita
- Cria um repositório novo chamado `epg-proxy` (público)

### 2. Fazer upload dos ficheiros
No repositório criado, faz upload destes 4 ficheiros:
- `app.py`
- `index.html`
- `requirements.txt`
- `render.yaml`

### 3. Criar conta no Render.com
- Vai a https://render.com
- Regista com a conta GitHub

### 4. Criar o serviço
- Clica em "New" → "Web Service"
- Liga ao teu repositório `epg-proxy`
- O Render detecta automaticamente o `render.yaml`
- Clica em "Create Web Service"

### 5. Aguardar deploy
- O primeiro deploy demora ~2-3 minutos
- Ficas com um URL tipo: `https://epg-proxy-xxxx.onrender.com`

### 6. Configurar no teu player
- O URL do EPG é: `https://epg-proxy-xxxx.onrender.com/epg.xml`
- A interface de gestão é: `https://epg-proxy-xxxx.onrender.com`

---

## Como usar a interface

1. Abre o URL da interface no browser
2. O EPG carrega automaticamente na primeira vez (pode demorar ~1 min)
3. Pesquisa o canal que queres ajustar
4. Usa os botões +/- para ajustar o offset em minutos
5. Clica ✓ para guardar
6. O offset fica guardado permanentemente

### Offset global
- Usa o campo "Offset global" para aplicar o mesmo valor a todos os canais de uma vez
- Por defeito está +1 minuto

---

## Notas importantes

### Render.com plano gratuito
- O serviço "adormece" após 15 minutos sem pedidos
- Quando o player pede o EPG, pode demorar ~30 segundos na primeira vez (wake up)
- Para evitar isto, considera o plano pago ($7/mês) ou usar um serviço de "ping" gratuito como UptimeRobot

### Atualização automática
- O EPG é atualizado de 6 em 6 horas automaticamente
- Podes forçar atualização manual na interface com o botão "Atualizar EPG"

---

## Estrutura dos ficheiros

```
epg-proxy/
├── app.py          # Servidor Python (Flask)
├── index.html      # Interface web
├── requirements.txt # Dependências Python
├── render.yaml     # Configuração do Render.com
├── offsets.json    # Offsets guardados (criado automaticamente)
└── epg_cache.xml   # EPG processado (criado automaticamente)
```
