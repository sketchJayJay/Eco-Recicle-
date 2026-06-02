function parseNumber(value) {
  if (!value) return 0;
  const raw = String(value).trim();
  if (raw.includes(',')) {
    return Number(raw.replace(/\./g, '').replace(',', '.')) || 0;
  }
  return Number(raw) || 0;
}

function formatMoney(value) {
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function formatKg(value) {
  return value.toLocaleString('pt-BR', { minimumFractionDigits: 3, maximumFractionDigits: 3 }) + ' kg';
}

function updateRowNumbers(items) {
  items.querySelectorAll('.item-row').forEach((row, index) => {
    const number = row.querySelector('.row-number');
    if (number) number.textContent = `#${index + 1}`;
  });
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
      const weight = parseNumber(row.querySelector('.weight')?.value);
      const price = parseNumber(row.querySelector('.price')?.value);
      const subtotal = weight * price;
      kg += weight;
      amount += subtotal;
      const subtotalText = row.querySelector('.subtotal strong');
      if (subtotalText) subtotalText.textContent = formatMoney(subtotal);
    });
    if (totalKg) totalKg.textContent = formatKg(kg);
    if (totalAmount) totalAmount.textContent = formatMoney(amount);
  }

  function addRow(focus = false) {
    const fragment = tpl.content.cloneNode(true);
    const row = fragment.querySelector('.item-row');
    const select = row.querySelector('.material-select');
    const price = row.querySelector('.price');
    const weight = row.querySelector('.weight');

    select.addEventListener('change', () => {
      const option = select.options[select.selectedIndex];
      price.value = option?.dataset?.price ? option.dataset.price.replace('.', ',') : '';
      setTimeout(() => weight.focus(), 50);
      recalc();
    });

    row.querySelectorAll('input, select').forEach(input => {
      input.addEventListener('input', recalc);
      input.addEventListener('change', recalc);
    });

    row.querySelector('.remove-item').addEventListener('click', () => {
      row.remove();
      if (!items.querySelector('.item-row')) addRow(true);
      updateRowNumbers(items);
      recalc();
    });

    items.appendChild(fragment);
    updateRowNumbers(items);
    recalc();
    if (focus) row.querySelector('.material-select')?.focus();
  }

  add.addEventListener('click', () => addRow(true));

  form.addEventListener('submit', () => {
    const btn = form.querySelector('[type="submit"]');
    if (btn) {
      btn.disabled = true;
      btn.dataset.originalText = btn.textContent;
      btn.textContent = btn.dataset.loadingText || 'Salvando...';
    }
  });

  addRow(false);
}

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
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') closeMenu();
  });

  sidebar.querySelectorAll('nav a').forEach(link => link.addEventListener('click', closeMenu));
}

function setupReceiptShare() {
  const btn = document.getElementById('shareReceipt');
  const receipt = document.querySelector('.thermal-receipt');
  if (!btn || !receipt) return;

  btn.addEventListener('click', async () => {
    const text = receipt.innerText.replace(/\n{3,}/g, '\n\n').trim();
    try {
      if (navigator.share) {
        await navigator.share({ title: document.title, text });
      } else if (navigator.clipboard) {
        await navigator.clipboard.writeText(text);
        btn.textContent = 'Copiado!';
        setTimeout(() => { btn.textContent = 'Compartilhar'; }, 1600);
      }
    } catch (_err) {
      // O usuário pode cancelar o compartilhamento; não precisa mostrar erro.
    }
  });
}

function setupPwaInstall() {
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/static/service-worker.js').catch(() => {});
    });
  }
}

document.addEventListener('DOMContentLoaded', setupPurchaseForm);
document.addEventListener('DOMContentLoaded', setupMobileShell);
document.addEventListener('DOMContentLoaded', setupReceiptShare);
document.addEventListener('DOMContentLoaded', setupPwaInstall);
