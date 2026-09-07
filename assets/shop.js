/* Cerberus Supply Archive: Shop JavaScript Engine */

(function () {
  'use strict';

  const PRODUCTS = [
    {
      id: 'cerberus-hat',
      title: 'CERBERUS 6-PANEL DAD CAP',
      type: 'HEADWEAR',
      price: 18.00,
      comparePrice: 24.00,
      image: 'assets/shop/cerberus-hat.jpg',
      subtitle: 'Unstructured Washed Cotton Twill / Custom Antique Brass Buckle',
      description: 'Classic unstructured low-profile 6-panel cap crafted from washed heavy chino cotton twill. Features high-density 3D direct embroidery of the three-headed Cerberus hound emblem on the front crown, stitched ventilation eyelets, curved visor, and an adjustable self-fabric strap with an engraved antique brass closure buckle.',
      specs: [
        '100% Washed Chino Cotton Twill',
        'Unstructured, low-profile 6-panel silhouette',
        'Raised 3D silver-white Cerberus embroidery on front',
        'Antique brass embossed slide buckle with tuck-in grommet',
        'One size fits all (Adjustable 54cm - 62cm / 21.25" - 24.4")',
        'Internal moisture-wicking sweatband'
      ],
      sizes: ['ONE SIZE'],
      sizeGuide: {
        columns: ['Size', 'Circumference (in)', 'Brim Length (in)', 'Crown Height (in)'],
        rows: [
          ['ONE SIZE', '21.25" - 24.4" (Adjustable)', '2.8"', '4.3"']
        ]
      }
    },
    {
      id: 'cerberus-tshirt',
      title: 'CERBERUS BOXY TEE',
      type: 'TOPS',
      price: 36.00,
      comparePrice: 45.00,
      image: 'assets/shop/cerberus-boxy-tee.png',
      subtitle: "Relaxed Boxy Tee / Cream",
      description: "A cream boxy tee with a detailed three-headed hound illustration and CERBERUS LABS lettering at the left chest. The relaxed shape pairs dropped shoulders with wide short sleeves and a ribbed crew neckline.",
      specs: [
        "Cream colorway",
        "Relaxed boxy silhouette with dropped shoulders",
        "Three-headed hound illustration at the left chest",
        "Ribbed crew neckline and wide short sleeves"
      ],
      sizes: ['S', 'M', 'L', 'XL', 'XXL'],
      sizeGuide: {
        columns: ['Size', 'Chest Width (in)', 'Body Length (in)', 'Sleeve (in)'],
        rows: [
          ['S', '19.0"', '27.5"', '8.0"'],
          ['M', '21.0"', '28.5"', '8.5"'],
          ['L', '23.0"', '29.5"', '9.0"'],
          ['XL', '25.0"', '30.5"', '9.5"'],
          ['XXL', '27.0"', '31.5"', '10.0"']
        ]
      }
    },
    {
      id: 'cerberus-crewneck',
      title: 'CERBERUS CREW',
      type: 'OUTERWEAR',
      price: 58.00,
      comparePrice: 70.00,
      image: 'assets/shop/cerberus-crew.png',
      subtitle: "Classic Crewneck / Heather White",
      description: "A heather white crewneck with a black three-headed Cerberus emblem and CERBERUS LABS lettering at the left chest. A clean everyday layer with a relaxed silhouette and ribbed neckline, cuffs, and hem.",
      specs: [
        "Heather white colorway",
        "Black Cerberus emblem at the left chest",
        "Ribbed crew neckline, cuffs, and hem",
        "Long sleeves with a relaxed silhouette"
      ],
      sizes: ['S', 'M', 'L', 'XL', 'XXL'],
      sizeGuide: {
        columns: ['Size', 'Chest Width (in)', 'Body Length (in)', 'Sleeve (in)'],
        rows: [
          ['S', '20.5"', '27.0"', '25.0"'],
          ['M', '22.0"', '28.0"', '25.5"'],
          ['L', '24.0"', '29.0"', '26.0"'],
          ['XL', '26.0"', '30.0"', '26.5"'],
          ['XXL', '28.0"', '31.0"', '27.0"']
        ]
      }
    },
    {
      id: 'cerberus-sweat-set',
      title: 'CERBERUS SWEAT SET',
      type: 'OUTERWEAR',
      price: 82.00,
      comparePrice: 95.00,
      image: 'assets/shop/cerberus-sweat-set.png',
      subtitle: "Zip Hoodie + Matching Sweatpants / Cream",
      description: "A coordinated cream sweat set featuring a full-zip hoodie and matching sweatpants. Detailed black Cerberus hounds and landscape artwork span the hoodie and one pant leg, with subtle CERBERUS LABS lettering at the chest.",
      specs: [
        "Two-piece set: zip hoodie and matching sweatpants",
        "Cream colorway with black hound and landscape artwork",
        "Full-length front zipper and hood",
        "Ribbed hoodie cuffs and hem",
        "Drawstring waistband and elastic pant cuffs"
      ],
      sizes: ['S', 'M', 'L', 'XL', 'XXL'],
      sizeGuide: null
    }
  ];

  const FREE_SHIPPING_THRESHOLD = 140.00;
  const STORAGE_KEY = 'cerberus_cart_items_v1';

  let cart = [];
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) cart = JSON.parse(saved);
  } catch (e) {
    cart = [];
  }

  function saveCart() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(cart));
    } catch (e) {}
    updateCartUI();
  }

  // Active modal product state
  let currentModalProduct = null;
  let selectedSize = 'M';
  let selectedQty = 1;

  // DOM Elements
  const cartOverlay = document.getElementById('cart-drawer-overlay');
  const cartDrawer = document.getElementById('cart-drawer');
  const cartCloseBtn = document.getElementById('cart-close-btn');
  const cartNavBtn = document.getElementById('cart-nav-btn');
  const cartNavBadge = document.getElementById('cart-nav-badge');
  const cartItemsList = document.getElementById('cart-items-list');
  const cartSubtotalEl = document.getElementById('cart-subtotal');
  const shippingFill = document.getElementById('shipping-progress-fill');
  const shippingMsg = document.getElementById('shipping-progress-msg');
  const checkoutBtn = document.getElementById('cart-checkout-btn');

  const productModal = document.getElementById('product-modal');
  const modalCloseBtn = document.getElementById('modal-close-btn');

  const checkoutModal = document.getElementById('checkout-modal');
  const checkoutCloseBtn = document.getElementById('checkout-close-btn');
  const checkoutForm = document.getElementById('checkout-form');
  const checkoutSummaryBox = document.getElementById('checkout-summary-box');

  // Render Product Grid
  function renderProducts(filter = 'ALL') {
    const grid = document.getElementById('products-grid');
    if (!grid) return;

    const filtered = filter === 'ALL' 
      ? PRODUCTS 
      : PRODUCTS.filter(p => p.type === filter);

    grid.innerHTML = filtered.map(p => `
      <article class="product-card" data-id="${p.id}">
        <div class="product-media" onclick="window.cerberusShop.openModal('${p.id}')">
          <img src="${p.image}" alt="${p.title}" loading="lazy" width="1200" height="800">
        </div>
        <div class="product-info">
          <div class="product-info-text">
            <span class="product-type">${p.type}</span>
            <h3 class="product-title" onclick="window.cerberusShop.openModal('${p.id}')">${p.title}</h3>
            <p class="product-subtitle">${p.subtitle}</p>
          </div>
          <div class="product-info-buy">
            <div class="product-price-row">
              <span class="product-price">$${p.price.toFixed(2)}</span>
              ${p.comparePrice ? `<span class="product-compare-price">$${p.comparePrice.toFixed(2)}</span>` : ''}
            </div>
            <div class="product-btn-group">
              <button type="button" class="btn-buy-direct" onclick="window.cerberusShop.quickAdd('${p.id}')">
                Add to Cart
              </button>
              <button type="button" class="btn-details" onclick="window.cerberusShop.openModal('${p.id}')" aria-label="View specifications">
                Details
              </button>
            </div>
          </div>
        </div>
      </article>
    `).join('');
  }

  // Open Product Detail Modal
  function openModal(productId) {
    const p = PRODUCTS.find(x => x.id === productId);
    if (!p || !productModal) return;

    currentModalProduct = p;
    selectedSize = p.sizes.includes('M') ? 'M' : p.sizes[0];
    selectedQty = 1;

    document.getElementById('modal-img').src = p.image;
    document.getElementById('modal-img').alt = p.title;
    document.getElementById('modal-type').textContent = p.type;
    document.getElementById('modal-title').textContent = p.title;
    document.getElementById('modal-price').textContent = `$${p.price.toFixed(2)}`;
    document.getElementById('modal-compare-price').textContent = p.comparePrice ? `$${p.comparePrice.toFixed(2)}` : '';
    document.getElementById('modal-desc').textContent = p.description;
    
    // Specs list
    const specsEl = document.getElementById('modal-specs');
    specsEl.innerHTML = p.specs.map(s => `<li>${s}</li>`).join('');

    // Sizing buttons
    const sizeContainer = document.getElementById('modal-sizes');
    sizeContainer.innerHTML = p.sizes.map(sz => `
      <button type="button" class="size-btn ${sz === selectedSize ? 'active' : ''}" onclick="window.cerberusShop.selectSize('${sz}')">
        ${sz}
      </button>
    `).join('');

    // Size Guide Box
    const sgBox = document.getElementById('size-guide-box');
    sgBox.classList.remove('visible');
    sgBox.innerHTML = p.sizeGuide ? `
      <h4>${p.title} — Garment Measurements</h4>
      <table class="size-table">
        <thead>
          <tr>${p.sizeGuide.columns.map(c => `<th>${c}</th>`).join('')}</tr>
        </thead>
        <tbody>
          ${p.sizeGuide.rows.map(r => `<tr>${r.map(d => `<td>${d}</td>`).join('')}</tr>`).join('')}
        </tbody>
      </table>
    ` : '<p>Measurements for the sweat set will be available soon.</p>';

    document.getElementById('modal-qty-val').textContent = selectedQty;
    
    const addBtn = document.getElementById('modal-add-btn');
    addBtn.textContent = 'Add to Cart — ' + `$${(p.price * selectedQty).toFixed(2)}`;
    addBtn.classList.remove('added');

    productModal.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    if (productModal) {
      productModal.classList.remove('open');
      document.body.style.overflow = '';
    }
  }

  function selectSize(size) {
    selectedSize = size;
    const buttons = document.querySelectorAll('#modal-sizes .size-btn');
    buttons.forEach(b => {
      b.classList.toggle('active', b.textContent.trim() === size);
    });
  }

  function adjustModalQty(delta) {
    selectedQty = Math.max(1, Math.min(10, selectedQty + delta));
    document.getElementById('modal-qty-val').textContent = selectedQty;
    if (currentModalProduct) {
      const addBtn = document.getElementById('modal-add-btn');
      addBtn.textContent = `Add to Cart — $${(currentModalProduct.price * selectedQty).toFixed(2)}`;
    }
  }

  function toggleSizeGuide() {
    const sgBox = document.getElementById('size-guide-box');
    if (sgBox) {
      sgBox.classList.toggle('visible');
    }
  }

  // Pre-order reservations. No payment is taken — the cart collects a
  // reservation (items + one email) that is POSTed to Web3Forms
  // (cerberus-shop-order) and mirrored in localStorage. Due today is $0.
  // The Web3Forms access key is public by design (safe in client-side code).
  const PREORDER_KEY = 'cerberus_preorders_v1';
  const WEB3FORMS_ENDPOINT = 'https://api.web3forms.com/submit';
  const WEB3FORMS_ACCESS_KEY = '0313e788-beda-4ad2-9d9c-2dc71ad3405c';

  function loadPreorders() {
    try {
      const saved = localStorage.getItem(PREORDER_KEY);
      return saved ? JSON.parse(saved) : [];
    } catch (e) {
      return [];
    }
  }

  function savePreorder(entry) {
    const all = loadPreorders();
    all.push(entry);
    try {
      localStorage.setItem(PREORDER_KEY, JSON.stringify(all));
    } catch (e) {}
  }

  // Cart Logic
  function addToCart(productId, size, qty = 1) {
    const p = PRODUCTS.find(x => x.id === productId);
    if (!p) return;

    const existingIndex = cart.findIndex(item => item.id === productId && item.size === size);
    if (existingIndex >= 0) {
      cart[existingIndex].qty += qty;
    } else {
      cart.push({
        id: p.id,
        title: p.title,
        price: p.price,
        image: p.image,
        size: size,
        qty: qty
      });
    }

    saveCart();
    openCart();
  }

  function quickAdd(productId) {
    const p = PRODUCTS.find(x => x.id === productId);
    if (!p) return;
    const defaultSize = p.sizes.includes('M') ? 'M' : p.sizes[0];
    addToCart(productId, defaultSize, 1);
  }

  function modalAddToCart() {
    if (!currentModalProduct) return;
    addToCart(currentModalProduct.id, selectedSize, selectedQty);

    const addBtn = document.getElementById('modal-add-btn');
    addBtn.textContent = 'ADDED TO CART ✓';
    addBtn.classList.add('added');
    setTimeout(() => {
      closeModal();
    }, 450);
  }

  function updateCartUI() {
    const totalCount = cart.reduce((acc, item) => acc + item.qty, 0);
    if (cartNavBadge) {
      cartNavBadge.textContent = totalCount;
    }

    const subtotal = cart.reduce((acc, item) => acc + (item.price * item.qty), 0);
    if (cartSubtotalEl) {
      cartSubtotalEl.textContent = `$${subtotal.toFixed(2)}`;
    }

    // Shipping threshold
    if (shippingFill && shippingMsg) {
      const diff = FREE_SHIPPING_THRESHOLD - subtotal;
      if (diff <= 0) {
        shippingFill.style.width = '100%';
        shippingMsg.innerHTML = '<span style="color:#0E9F42; font-weight:700;">✓ YOU UNLOCKED FREE WORLDWIDE SHIPPING!</span>';
      } else {
        const pct = Math.min(100, Math.max(0, (subtotal / FREE_SHIPPING_THRESHOLD) * 100));
        shippingFill.style.width = `${pct}%`;
        shippingMsg.innerHTML = `Add <strong>$${diff.toFixed(2)}</strong> more for <strong>FREE Worldwide Shipping</strong>`;
      }
    }

    // Render items
    if (cartItemsList) {
      if (cart.length === 0) {
        cartItemsList.innerHTML = `
          <div class="cart-empty-state">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom:12px; opacity:0.6;">
              <path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><path d="M3 6h18"/><path d="M16 10a4 4 0 0 1-8 0"/>
            </svg>
            <p>Your supply cart is currently empty.<br>Select apparel from the collection above.</p>
            <button type="button" class="btn-details" onclick="window.cerberusShop.closeCart()">Return to Archive</button>
          </div>
        `;
        if (checkoutBtn) checkoutBtn.disabled = true;
      } else {
        if (checkoutBtn) checkoutBtn.disabled = false;
        cartItemsList.innerHTML = cart.map((item, index) => `
          <div class="cart-item-card">
            <img src="${item.image}" alt="${item.title}" class="cart-item-thumb">
            <div class="cart-item-details">
              <div>
                <h4 class="cart-item-name">${item.title}</h4>
                <div class="cart-item-size">Size: <strong>${item.size}</strong></div>
              </div>
              <div class="cart-item-price">$${(item.price * item.qty).toFixed(2)}</div>
            </div>
            <div class="cart-item-actions">
              <button type="button" class="cart-item-remove" onclick="window.cerberusShop.removeCartItem(${index})" title="Remove item">✕</button>
              <div class="cart-item-stepper">
                <button type="button" onclick="window.cerberusShop.updateCartQty(${index}, -1)">-</button>
                <span>${item.qty}</span>
                <button type="button" onclick="window.cerberusShop.updateCartQty(${index}, 1)">+</button>
              </div>
            </div>
          </div>
        `).join('');
      }
    }
  }

  function updateCartQty(index, delta) {
    if (!cart[index]) return;
    cart[index].qty += delta;
    if (cart[index].qty <= 0) {
      cart.splice(index, 1);
    }
    saveCart();
  }

  function removeCartItem(index) {
    if (!cart[index]) return;
    cart.splice(index, 1);
    saveCart();
  }

  function openCart() {
    if (cartOverlay) {
      cartOverlay.classList.add('open');
      document.body.style.overflow = 'hidden';
    }
  }

  function closeCart() {
    if (cartOverlay) {
      cartOverlay.classList.remove('open');
      document.body.style.overflow = '';
    }
  }

  // Pre-order reservation (no payment). POSTs items + email to Web3Forms,
  // mirrors the reservation locally, and shows a reservation code.
  // Due today is always $0.00.
  function openCheckout() {
    if (cart.length === 0) return;
    closeCart();

    const subtotal = cart.reduce((acc, item) => acc + (item.price * item.qty), 0);

    if (checkoutSummaryBox) {
      checkoutSummaryBox.innerHTML = `
        <div style="font-weight:700; margin-bottom:8px; border-bottom:1px dashed #CCC; padding-bottom:6px;">PRE-ORDER RESERVATION (${cart.reduce((a,c)=>a+c.qty,0)} ITEMS)</div>
        ${cart.map(i => `<div style="display:flex; justify-content:space-between; margin-bottom:4px;"><span>${i.qty}× ${i.title} (${i.size})</span><span>$${(i.price * i.qty).toFixed(2)}</span></div>`).join('')}
        <div style="display:flex; justify-content:space-between; margin-top:8px; border-top:1px dashed #CCC; padding-top:6px;">
          <span>Estimated total at fulfillment:</span><strong>$${subtotal.toFixed(2)}</strong>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:14px; font-weight:700; margin-top:6px; color:var(--shop-ink);">
          <span>Due today:</span><span>$0.00</span>
        </div>
      `;
    }

    const formFields = document.getElementById('checkout-fields');
    if (formFields) formFields.style.display = '';

    if (checkoutModal) {
      checkoutModal.classList.add('open');
      document.body.style.overflow = 'hidden';
    }
  }

  function closeCheckout() {
    if (checkoutModal) {
      checkoutModal.classList.remove('open');
      document.body.style.overflow = '';
    }
  }

  function showCheckoutError(msg) {
    clearCheckoutError();
    const fields = document.getElementById('checkout-fields');
    if (!fields) return;
    const p = document.createElement('p');
    p.id = 'checkout-error';
    p.setAttribute('role', 'alert');
    p.style.cssText = 'margin:12px 0 0; padding:10px 12px; border:1px solid #C0392B; color:#7B241C; background:#FDEDEC; font:400 12px/1.6 var(--font-mono);';
    p.textContent = msg;
    fields.appendChild(p);
  }

  function clearCheckoutError() {
    const prev = document.getElementById('checkout-error');
    if (prev) prev.remove();
  }

  async function handleCheckoutSubmit(e) {
    e.preventDefault();
    const emailInput = document.getElementById('checkout-email');
    const email = (emailInput?.value || '').trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      if (emailInput) emailInput.focus();
      return;
    }
    const submitBtn = checkoutForm ? checkoutForm.querySelector('button[type="submit"]') : null;
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Reserving…';
    }
    clearCheckoutError();

    const code = 'CRB-PRE-' + Math.floor(100000 + Math.random() * 900000);
    const items = cart.map(i => ({ id: i.id, title: i.title, size: i.size, qty: i.qty, price: i.price }));
    const subtotal = cart.reduce((acc, item) => acc + (item.price * item.qty), 0);
    const itemCount = cart.reduce((a, c) => a + c.qty, 0);
    const itemLines = items.map(i => `${i.qty}x ${i.title} (${i.size}) — $${(i.price * i.qty).toFixed(2)}`);

    let sent = false;
    try {
      const res = await fetch(WEB3FORMS_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({
          access_key: WEB3FORMS_ACCESS_KEY,
          subject: `Cerberus pre-order ${code} — $${subtotal.toFixed(2)} est.`,
          from_name: 'Cerberus Supply Pre-Order',
          email,
          message: `Reservation ${code}\n${itemLines.join('\n')}\nEstimated total at fulfillment: $${subtotal.toFixed(2)}\nDue today: $0.00`,
          reservation_code: code,
          items: itemLines.join('; '),
          estimated_total: `$${subtotal.toFixed(2)}`,
          due_today: '$0.00',
          botcheck: ''
        })
      });
      const data = await res.json().catch(() => ({}));
      sent = res.ok && data.success === true;
    } catch (err) {
      sent = false;
    }

    if (!sent) {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Reserve Pre-Order — $0 Due Today ↗';
      }
      showCheckoutError('Reservation could not be sent (network error). Your cart is intact — check your connection and try again.');
      return;
    }

    savePreorder({ code, email, items, subtotal, createdAt: new Date().toISOString(), sent: true });

    if (checkoutSummaryBox) {
      const escEmail = email.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      checkoutSummaryBox.innerHTML = `
        <div style="text-align:center; padding: 24px 12px;">
          <div style="font-size:32px; margin-bottom:12px;">✓</div>
          <h3 style="font: 400 16px var(--font-pixel); text-transform:uppercase; margin-bottom:8px;">RESERVED</h3>
          <p style="font:700 13px var(--font-mono); margin-bottom:12px;">${code}</p>
          <p style="font:400 12px/1.7 var(--font-mono); color:var(--shop-muted);">
            ${itemCount} item(s) held for <strong>${escEmail}</strong>.<br>
            No charge today — we email you a checkout link when production opens.<br>
            Reservation sent to our supply team and kept in this browser.
          </p>
        </div>
      `;
    }

    const formFields = document.getElementById('checkout-fields');
    if (formFields) formFields.style.display = 'none';

    // Clear cart — items now live on the reservation.
    cart = [];
    saveCart();
  }

  // Filter Pills Event Handling
  function initFilterPills() {
    const pills = document.querySelectorAll('.shop-pill');
    pills.forEach(pill => {
      pill.addEventListener('click', () => {
        pills.forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        const filter = pill.getAttribute('data-filter') || 'ALL';
        renderProducts(filter);
      });
    });
  }

  // Bind Listeners
  document.addEventListener('DOMContentLoaded', () => {
    renderProducts('ALL');
    initFilterPills();
    updateCartUI();

    if (cartNavBtn) cartNavBtn.addEventListener('click', openCart);
    if (cartCloseBtn) cartCloseBtn.addEventListener('click', closeCart);
    if (cartOverlay) {
      cartOverlay.addEventListener('click', (e) => {
        if (e.target === cartOverlay) closeCart();
      });
    }

    if (modalCloseBtn) modalCloseBtn.addEventListener('click', closeModal);
    if (productModal) {
      productModal.addEventListener('click', (e) => {
        if (e.target === productModal) closeModal();
      });
    }

    if (checkoutBtn) checkoutBtn.addEventListener('click', openCheckout);
    if (checkoutCloseBtn) checkoutCloseBtn.addEventListener('click', closeCheckout);
    if (checkoutModal) {
      checkoutModal.addEventListener('click', (e) => {
        if (e.target === checkoutModal) closeCheckout();
      });
    }
    if (checkoutForm) {
      checkoutForm.addEventListener('submit', handleCheckoutSubmit);
    }

    // Keyboard ESC to close any open modal
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        closeModal();
        closeCart();
        closeCheckout();
      }
    });
  });

  // Global exports for inline button triggers
  window.cerberusShop = {
    openModal,
    closeModal,
    selectSize,
    adjustModalQty,
    toggleSizeGuide,
    modalAddToCart,
    quickAdd,
    addToCart,
    openCart,
    closeCart,
    updateCartQty,
    removeCartItem,
    openCheckout,
    closeCheckout,
    loadPreorders
  };

})();
