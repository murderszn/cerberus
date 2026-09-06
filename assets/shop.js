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
      id: 'cerberus-crewneck',
      title: 'CERBERUS REBEL FRENCH TERRY CREWNECK',
      type: 'OUTERWEAR',
      price: 58.00,
      comparePrice: 70.00,
      image: 'assets/shop/cerberus-crewneck.jpg',
      subtitle: '11 oz. French Terry Pullover / Heather Chalk White',
      description: 'Versatile mid-weight pullover engineered for transitional weather and continuous workstation wear. Crafted from breathable 100% California-grown cotton loopback French Terry. Features an antique heather chalk white base accented by bold contrast black Cerberus typography and the iconic Cerberus tri-head hound crest.',
      specs: [
        '100% California Cotton French Terry (11 oz. / 350 GSM)',
        'Garment-dyed chalk heather white, shrink-free finish',
        'V-notch neck insert with wide ribbed hem and cuffs',
        'High-density screenprint emblem on chest',
        'Tailored athletic taper with comfortable shoulder articulation',
        'Sewn in Los Angeles, CA'
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
      id: 'cerberus-tshirt',
      title: 'CERBERUS GUARDIAN T-SHIRT',
      type: 'TOPS',
      price: 36.00,
      comparePrice: 45.00,
      image: 'assets/shop/cerberus-tshirt.jpg',
      subtitle: '7.5 oz. Heavyweight Combed Cotton / Vintage Pigment Wash',
      description: 'The definitive Cerberus developer tee. Constructed from a beefy 7.5 oz. vintage dye-washed cotton jersey reminiscent of 90s heavyweight lifting shirts. Boasts a thick 1-inch bound ribbed collar, relaxed boxy cut, and crisp chest graphic of the Cerberus hound triumvirate with clean CERBERUS LABS branding.',
      specs: [
        '100% Ring-Spun Cotton (7.5 oz. Heavyweight Jersey)',
        'Vintage garment dye-washed in charcoal black',
        '1" thick tight collar binding that will never bacon',
        'Center chest screenprint with micro-halftone detail',
        'Reinforced twin needle stitching at hem and sleeves',
        'Made in USA'
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
      id: 'cerberus-hoodie',
      title: 'CERBERUS HEAVY FLEECE HOODIE',
      type: 'OUTERWEAR',
      price: 82.00,
      comparePrice: 95.00,
      image: 'assets/shop/cerberus-hoodie.jpg',
      subtitle: '14 oz. Heavyweight USA Combed Cotton / Oversized Boxy Cut',
      description: 'Engineered for late-night research sessions and cold server corridors. Cut from ultra-dense 14 oz. (450 GSM) combed cotton fleece, preshrunk with a wide boxy drape, drop shoulders, double-lined hood without drawstrings, and seamless heavy ribbed cuffs. The back features a screenprinted rendering of the three-headed Cerberus guardian hounds in high-density archival ink.',
      specs: [
        '100% Combed USA Cotton (14 oz. / 450 GSM)',
        'Oversized boxy streetwear silhouette with drop shoulders',
        'Large Cerberus three-headed canine screenprint on back',
        'Cerberus Armored Division woven label inside collar',
        'Pre-washed and shrink-free; garment dyed in Los Angeles, CA',
        'Model is 6\'1" wearing size L'
      ],
      sizes: ['S', 'M', 'L', 'XL', 'XXL'],
      sizeGuide: {
        columns: ['Size', 'Chest Width (in)', 'Body Length (in)', 'Sleeve Length (in)'],
        rows: [
          ['S', '21.5"', '26.5"', '24.0"'],
          ['M', '23.5"', '27.5"', '24.5"'],
          ['L', '25.5"', '28.5"', '25.0"'],
          ['XL', '27.5"', '29.5"', '25.5"'],
          ['XXL', '29.5"', '30.5"', '26.0"']
        ]
      }
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
    sgBox.innerHTML = `
      <h4>${p.title} — Garment Measurements</h4>
      <table class="size-table">
        <thead>
          <tr>${p.sizeGuide.columns.map(c => `<th>${c}</th>`).join('')}</tr>
        </thead>
        <tbody>
          ${p.sizeGuide.rows.map(r => `<tr>${r.map(d => `<td>${d}</td>`).join('')}</tr>`).join('')}
        </tbody>
      </table>
    `;

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

  // Simulated Checkout
  function openCheckout() {
    if (cart.length === 0) return;
    closeCart();

    const subtotal = cart.reduce((acc, item) => acc + (item.price * item.qty), 0);
    const shipping = subtotal >= FREE_SHIPPING_THRESHOLD ? 0.00 : 12.00;
    const total = subtotal + shipping;

    if (checkoutSummaryBox) {
      checkoutSummaryBox.innerHTML = `
        <div style="font-weight:700; margin-bottom:8px; border-bottom:1px dashed #CCC; padding-bottom:6px;">ORDER SUMMARY (${cart.reduce((a,c)=>a+c.qty,0)} ITEMS)</div>
        ${cart.map(i => `<div style="display:flex; justify-content:space-between; margin-bottom:4px;"><span>${i.qty}× ${i.title} (${i.size})</span><span>$${(i.price * i.qty).toFixed(2)}</span></div>`).join('')}
        <div style="display:flex; justify-content:space-between; margin-top:8px; border-top:1px dashed #CCC; padding-top:6px;">
          <span>Subtotal:</span><strong>$${subtotal.toFixed(2)}</strong>
        </div>
        <div style="display:flex; justify-content:space-between;">
          <span>Shipping:</span><strong>${shipping === 0 ? 'FREE' : `$${shipping.toFixed(2)}`}</strong>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:14px; font-weight:700; margin-top:6px; color:var(--shop-ink);">
          <span>Estimated Total:</span><span>$${total.toFixed(2)} USD</span>
        </div>
      `;
    }

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

  function handleCheckoutSubmit(e) {
    e.preventDefault();
    const orderNumber = 'CRB-' + Math.floor(100000 + Math.random() * 900000);
    const email = document.getElementById('checkout-email')?.value || 'security@cerberus.internal';

    if (checkoutSummaryBox) {
      checkoutSummaryBox.innerHTML = `
        <div style="text-align:center; padding: 24px 12px;">
          <div style="font-size:32px; margin-bottom:12px;">✓</div>
          <h3 style="font: 400 16px var(--font-pixel); text-transform:uppercase; margin-bottom:8px;">ORDER CONFIRMED</h3>
          <p style="font:700 13px var(--font-mono); margin-bottom:12px;">ORDER #${orderNumber}</p>
          <p style="font:400 12px/1.7 var(--font-mono); color:var(--shop-muted);">
            Receipt sent to <strong>${email}</strong>.<br>
            Estimated production & dispatch lead time: 3-5 weeks.<br>
            Tracking will be provided once dispatched from Los Angeles, CA.
          </p>
        </div>
      `;
    }

    const formFields = document.getElementById('checkout-fields');
    if (formFields) formFields.style.display = 'none';

    // Clear cart
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
    closeCheckout
  };

})();
