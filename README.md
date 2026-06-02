# Sistema Eco Recicle

Sistema web para reciclagem, feito para usar no celular: compras por kg, vendas/retiradas do caminhão, materiais com preço automático, pessoas cadastradas, recibo térmico para cliente, comprovante de venda, relatórios e exportação CSV.

## O que tem nessa versão

- Layout responsivo para celular, com menu lateral e atalhos fixos na parte de baixo.
- Compra de materiais dos clientes/fornecedores.
- Recibo de compra em formato térmico 58mm, sem assinatura.
- Venda/retirada do caminhão, para registrar quando o dono da reciclagem recebe.
- Comprovante de venda/recebimento em formato térmico.
- Preço de compra/kg e preço de venda/kg separados.
- Relatório com total pago, total recebido e resultado bruto.
- Exportação CSV de compras e vendas.
- Manifest PWA para adicionar o sistema na tela inicial do celular.

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

Esses valores entram como preço de compra e também como preço inicial de venda. Depois dá para ajustar o preço de venda em **Materiais**.

## Como usar no celular

1. Publique no Coolify.
2. Abra o domínio do sistema no navegador do celular.
3. No Android/Chrome, toque nos três pontinhos e escolha **Adicionar à tela inicial**.
4. No iPhone/Safari, toque em compartilhar e escolha **Adicionar à Tela de Início**.

A impressão do recibo térmico depende da impressora Bluetooth estar configurada no celular. Normalmente, no Android, a impressora aparece pelo serviço/app da própria impressora e o navegador manda imprimir por ali.

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
