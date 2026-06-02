# Sistema Eco Recicle — versão celular melhorada

Sistema web para reciclagem, feito para usar no celular como um aplicativo: compras por kg, vendas/retiradas do caminhão, estoque automático, recibo térmico para cliente, comprovante de venda, relatórios e exportação CSV.

## O que melhorou nessa versão

- Tela inicial com botões grandes para **Nova compra**, **Caminhão**, **Estoque** e **Relatório**.
- Melhor uso no celular: campos maiores, botões fixos e total sempre visível durante o lançamento.
- Nova tela de **Estoque atual**: calcula automaticamente o saldo por material.
- O estoque é calculado assim: **kg comprado - kg vendido para o caminhão**.
- Mostra **valor estimado de venda do estoque**, usando o preço de venda/kg.
- Avisa se algum material ficar com estoque negativo.
- Compra agora tem **forma de pagamento**: Pix, dinheiro, cartão, fiado ou outro.
- Venda do caminhão agora tem **forma de recebimento**: Pix, dinheiro, cartão, transferência ou outro.
- Recibo e comprovante ganharam botão de **compartilhar** pelo celular.
- Recibo térmico continua em **58mm**, sem assinaturas, para impressora pequena Bluetooth.
- Lista de compras e recebimentos em cards mais fáceis de usar no celular.
- PWA: pode adicionar na tela inicial do celular.

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

Esses valores entram como preço de compra e também como preço inicial de venda. Depois dá para ajustar em **Materiais**.

## Fluxo recomendado

1. Quando o cliente levar material para vender, abra **Nova compra**.
2. Escolha o fornecedor, material, peso e forma de pagamento.
3. Imprima o recibo térmico para entregar ao cliente.
4. Quando o caminhão buscar material, abra **Caminhão**.
5. Lance o material vendido, peso, preço de venda/kg e forma de recebimento.
6. Veja o saldo em **Estoque** e o resultado em **Relatórios**.

## Como usar no celular

1. Publique no Coolify.
2. Abra o domínio do sistema no navegador do celular.
3. No Android/Chrome, toque nos três pontinhos e escolha **Adicionar à tela inicial**.
4. No iPhone/Safari, toque em compartilhar e escolha **Adicionar à Tela de Início**.

A impressão do recibo térmico depende da impressora Bluetooth estar configurada no celular. Normalmente, no Android, a impressora aparece pelo app/serviço da própria impressora e o navegador manda imprimir por ali.

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

## Backup

O banco fica em `/app/data/eco_recicle.sqlite3`. Faça backup dessa pasta quando o sistema estiver em produção.
