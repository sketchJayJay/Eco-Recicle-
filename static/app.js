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

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = src;
  });
}

function wrapReceiptText(ctx, text, maxWidth) {
  const content = String(text || '').trim();
  if (!content) return [''];
  const words = content.split(/\s+/);
  const lines = [];
  let current = words[0] || '';
  for (let i = 1; i < words.length; i += 1) {
    const test = `${current} ${words[i]}`;
    if (ctx.measureText(test).width <= maxWidth) {
      current = test;
    } else {
      lines.push(current);
      current = words[i];
    }
  }
  if (current) lines.push(current);
  return lines.length ? lines : [''];
}

async function buildReceiptImage(receipt) {
  const canvasWidth = 696;
  const padding = 24;
  const contentWidth = canvasWidth - padding * 2;
  const left = padding;
  const right = canvasWidth - padding;

  const logoSrc = receipt.querySelector('.thermal-logo img')?.getAttribute('src') || '';
  const title = receipt.querySelector('.thermal-title h2')?.innerText?.trim() || 'RECIBO';
  const subtitle = receipt.querySelector('.thermal-title p')?.innerText?.trim() || '';
  const meta = Array.from(receipt.querySelectorAll('.thermal-meta p')).map(p => p.innerText.trim()).filter(Boolean);
  const items = Array.from(receipt.querySelectorAll('.thermal-items > *')).map(item => ({
    name: item.querySelector('.thermal-item-name')?.innerText?.trim() || item.innerText.trim(),
    calcLeft: item.querySelector('.thermal-item-calc span')?.innerText?.trim() || '',
    calcRight: item.querySelector('.thermal-item-calc strong')?.innerText?.trim() || ''
  })).filter(item => item.name || item.calcLeft || item.calcRight);
  const totals = Array.from(receipt.querySelectorAll('.thermal-totals div')).map(div => ({
    label: div.querySelector('span')?.innerText?.trim() || '',
    value: div.querySelector('strong')?.innerText?.trim() || ''
  })).filter(row => row.label || row.value);
  const notes = receipt.querySelector('.receipt-notes')?.innerText?.trim() || '';
  const footer = Array.from(receipt.querySelectorAll('.thermal-footer p, .thermal-footer small')).map(el => el.innerText.trim()).filter(Boolean);

  const measureCanvas = document.createElement('canvas');
  const ctxM = measureCanvas.getContext('2d');
  let y = padding;
  let logo = null;

  if (logoSrc) {
    try {
      logo = await loadImage(logoSrc);
      const ratio = logo.naturalHeight / logo.naturalWidth || 0.35;
      const logoWidth = Math.min(contentWidth * 0.92, 520);
      y += logoWidth * ratio + 12;
    } catch (_err) {
      logo = null;
    }
  }

  y += 10 + 28;
  if (subtitle) y += 20;
  y += 10;

  ctxM.font = '20px Arial';
  meta.forEach(line => {
    y += wrapReceiptText(ctxM, line, contentWidth).length * 20;
  });
  y += 12;

  ctxM.font = 'bold 22px Arial';
  items.forEach(item => {
    y += wrapReceiptText(ctxM, item.name.toUpperCase(), contentWidth).length * 24;
    ctxM.font = '20px Arial';
    y += Math.max(wrapReceiptText(ctxM, item.calcLeft, contentWidth - 170).length * 20, 20) + 14;
    ctxM.font = 'bold 22px Arial';
  });

  y += 10;
  totals.forEach(row => {
    ctxM.font = /total/i.test(row.label) ? 'bold 22px Arial' : 'bold 20px Arial';
    y += Math.max(wrapReceiptText(ctxM, row.label, contentWidth - 170).length * 20, 20) + 6;
  });

  if (notes) {
    ctxM.font = '20px Arial';
    y += wrapReceiptText(ctxM, notes, contentWidth).length * 20 + 8;
  }

  if (footer.length) {
    footer.forEach((line, index) => {
      ctxM.font = index === footer.length - 1 ? '16px Arial' : 'bold 18px Arial';
      y += wrapReceiptText(ctxM, line, contentWidth).length * (index === footer.length - 1 ? 18 : 20);
    });
  }

  const canvas = document.createElement('canvas');
  canvas.width = canvasWidth;
  canvas.height = Math.max(Math.ceil(y + padding), 340);
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#111';
  ctx.strokeStyle = '#111';
  ctx.textBaseline = 'top';

  let drawY = padding;

  function drawDashedLine() {
    ctx.save();
    ctx.setLineDash([8, 6]);
    ctx.beginPath();
    ctx.moveTo(left, drawY);
    ctx.lineTo(right, drawY);
    ctx.stroke();
    ctx.restore();
    drawY += 10;
  }

  if (logo) {
    const logoWidth = Math.min(contentWidth * 0.92, 520);
    const ratio = logo.naturalHeight / logo.naturalWidth || 0.35;
    const logoHeight = logoWidth * ratio;
    const x = (canvas.width - logoWidth) / 2;
    ctx.drawImage(logo, x, drawY, logoWidth, logoHeight);
    drawY += logoHeight + 12;
  }

  drawDashedLine();
  ctx.font = 'bold 24px Arial';
  ctx.fillText(title, (canvas.width - ctx.measureText(title).width) / 2, drawY);
  drawY += 28;

  if (subtitle) {
    ctx.font = 'bold 18px Arial';
    wrapReceiptText(ctx, subtitle, contentWidth).forEach(line => {
      ctx.fillText(line, (canvas.width - ctx.measureText(line).width) / 2, drawY);
      drawY += 20;
    });
  }

  drawDashedLine();
  ctx.font = '20px Arial';
  meta.forEach(line => {
    wrapReceiptText(ctx, line, contentWidth).forEach(part => {
      ctx.fillText(part, left, drawY);
      drawY += 20;
    });
  });

  drawDashedLine();
  items.forEach(item => {
    ctx.font = 'bold 22px Arial';
    wrapReceiptText(ctx, item.name.toUpperCase(), contentWidth).forEach(part => {
      ctx.fillText(part, left, drawY);
      drawY += 24;
    });
    ctx.font = '20px Arial';
    const leftLines = wrapReceiptText(ctx, item.calcLeft, contentWidth - 170);
    const blockHeight = Math.max(leftLines.length * 20, 20);
    leftLines.forEach((part, index) => ctx.fillText(part, left, drawY + index * 20));
    if (item.calcRight) {
      ctx.font = 'bold 20px Arial';
      ctx.fillText(item.calcRight, right - ctx.measureText(item.calcRight).width, drawY);
    }
    drawY += blockHeight + 6;
    ctx.save();
    ctx.setLineDash([3, 4]);
    ctx.strokeStyle = '#bcbcbc';
    ctx.beginPath();
    ctx.moveTo(left, drawY);
    ctx.lineTo(right, drawY);
    ctx.stroke();
    ctx.restore();
    drawY += 8;
  });

  drawDashedLine();
  totals.forEach(row => {
    const isGrand = /total/i.test(row.label);
    ctx.font = isGrand ? 'bold 22px Arial' : 'bold 20px Arial';
    const labelLines = wrapReceiptText(ctx, row.label, contentWidth - 170);
    const rowHeight = Math.max(labelLines.length * 20, 20);
    labelLines.forEach((part, index) => ctx.fillText(part, left, drawY + index * 20));
    ctx.font = isGrand ? 'bold 24px Arial' : 'bold 20px Arial';
    ctx.fillText(row.value, right - ctx.measureText(row.value).width, drawY);
    drawY += rowHeight + 6;
  });

  if (notes) {
    drawDashedLine();
    ctx.font = '20px Arial';
    wrapReceiptText(ctx, notes, contentWidth).forEach(part => {
      ctx.fillText(part, left, drawY);
      drawY += 20;
    });
  }

  if (footer.length) {
    drawDashedLine();
    footer.forEach((line, index) => {
      ctx.font = index === footer.length - 1 ? '16px Arial' : 'bold 18px Arial';
      wrapReceiptText(ctx, line, contentWidth).forEach(part => {
        ctx.fillText(part, (canvas.width - ctx.measureText(part).width) / 2, drawY);
        drawY += index === footer.length - 1 ? 18 : 20;
      });
    });
  }

  return new Promise(resolve => canvas.toBlob(blob => resolve(blob), 'image/png'));
}

function setupReceiptShare() {
  const btn = document.getElementById('shareReceipt');
  const receipt = document.querySelector('.thermal-receipt');
  if (!btn || !receipt) return;

  btn.addEventListener('click', async () => {
    const original = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Gerando imagem...';
    try {
      const blob = await buildReceiptImage(receipt);
      if (!blob) throw new Error('Erro ao gerar imagem');
      const fileName = `recibo-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')}.png`;
      const file = new File([blob], fileName, { type: 'image/png' });

      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({ title: document.title || 'Recibo', files: [file] });
      } else {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = fileName;
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      }
    } catch (_err) {
      // o usuário pode cancelar ou o navegador pode bloquear o compartilhamento
    } finally {
      btn.disabled = false;
      btn.textContent = original || 'Compartilhar recibo';
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
