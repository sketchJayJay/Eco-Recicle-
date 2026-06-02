function parseNumber(value) {
  if (!value) return 0;
  return Number(String(value).replace(',', '.')) || 0;
}

function formatMoney(value) {
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function formatKg(value) {
  return value.toLocaleString('pt-BR', { minimumFractionDigits: 3, maximumFractionDigits: 3 }) + ' kg';
}

function setupPurchaseForm() {
  const form = document.getElementById('purchaseForm');
  const items = document.getElementById('items');
  const tpl = document.getElementById('itemTemplate');
  const add = document.getElementById('addItem');
  const totalKg = document.getElementById('totalKg');
  const totalAmount = document.getElementById('totalAmount');
  if (!form || !items || !tpl || !add) return;

  function recalc() {
    let kg = 0;
    let amount = 0;
    items.querySelectorAll('.item-row').forEach(row => {
      const weight = parseNumber(row.querySelector('.weight').value);
      const price = parseNumber(row.querySelector('.price').value);
      const subtotal = weight * price;
      kg += weight;
      amount += subtotal;
      row.querySelector('.subtotal strong').textContent = formatMoney(subtotal);
    });
    totalKg.textContent = formatKg(kg);
    totalAmount.textContent = formatMoney(amount);
  }

  function addRow() {
    const fragment = tpl.content.cloneNode(true);
    const row = fragment.querySelector('.item-row');
    const select = row.querySelector('.material-select');
    const price = row.querySelector('.price');
    select.addEventListener('change', () => {
      const option = select.options[select.selectedIndex];
      price.value = option?.dataset?.price ? option.dataset.price.replace('.', ',') : '';
      recalc();
    });
    row.querySelectorAll('input, select').forEach(input => input.addEventListener('input', recalc));
    row.querySelector('.remove-item').addEventListener('click', () => {
      row.remove();
      if (!items.querySelector('.item-row')) addRow();
      recalc();
    });
    items.appendChild(fragment);
    recalc();
  }

  add.addEventListener('click', addRow);
  addRow();
}

document.addEventListener('DOMContentLoaded', setupPurchaseForm);

function setupMobileShell() {
  const sidebar = document.getElementById('sidebar');
  const openBtn = document.getElementById('openMenu');
  const closeBtn = document.getElementById('closeMenu');
  const overlay = document.getElementById('menuOverlay');
  if (!sidebar || !openBtn || !closeBtn || !overlay) return;

  function openMenu() {
    sidebar.classList.add('open');
    overlay.classList.add('show');
    document.body.style.overflow = 'hidden';
  }

  function closeMenu() {
    sidebar.classList.remove('open');
    overlay.classList.remove('show');
    document.body.style.overflow = '';
  }

  openBtn.addEventListener('click', openMenu);
  closeBtn.addEventListener('click', closeMenu);
  overlay.addEventListener('click', closeMenu);

  sidebar.querySelectorAll('nav a').forEach(link => link.addEventListener('click', closeMenu));
}

function setupPwaInstall() {
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/static/service-worker.js').catch(() => {});
    });
  }
}

document.addEventListener('DOMContentLoaded', setupMobileShell);
document.addEventListener('DOMContentLoaded', setupPwaInstall);
