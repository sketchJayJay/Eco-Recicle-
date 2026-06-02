# Sistema Eco Recicle

Sistema web simples para reciclagem: compras por kg, materiais com preço automático, fornecedores, recibo de compra, relatórios e exportação CSV.

## Login padrão

- Usuário: `admin`
- Senha: `123456`

No Coolify, troque usando variáveis de ambiente:

```env
ADMIN_USER=admin
ADMIN_PASSWORD=sua_senha_forte
SECRET_KEY=uma_chave_grande
COMPANY_NAME=Eco Recicle
DATA_DIR=/app/data
```

## Materiais já cadastrados

- Papelão: R$ 0,30/kg
- Papel: R$ 0,20/kg
- Filme: R$ 0,30/kg
- Plástico duro: R$ 0,10/kg
- Pet: R$ 0,50/kg
- Alumínio: R$ 8,00/kg
- Metal: R$ 18,00/kg
- Cobre: R$ 40,00/kg
- Fiação de cobre: R$ 15,00/kg
- Ferro: R$ 0,30/kg
- Bateria: R$ 2,00/kg

## Rodar localmente

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
python app.py
```

Acesse: `http://localhost:5000`

## Rodar com Docker

```bash
docker compose up --build -d
```

## Coolify

1. Suba este projeto no GitHub.
2. No Coolify, crie um novo app apontando para o repositório.
3. Tipo: Dockerfile.
4. Porta: `5000`.
5. Configure as variáveis de ambiente acima.
6. Adicione volume persistente em `/app/data`, para não perder o banco SQLite.

## Observação

O banco fica em `/app/data/eco_recicle.sqlite3`. Faça backup dessa pasta quando o sistema estiver em produção.
