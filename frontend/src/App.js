// ─────────────────────────────────────────────
// App.js  –  single-page frontend for the microservice shop
//
// Two tabs:
//   • Products – list, add, delete products (calls Inventory API :8000)
//   • Orders   – place orders and track their status (calls Payment API :8001)
//
// Order status flow:  pending → completed (or refunded)
// The app auto-polls every 3 s while any order is still "pending".
// ─────────────────────────────────────────────

import { useState, useEffect, useCallback } from 'react';
import './App.css';

// Base URLs for the two backend services
const INVENTORY = 'http://localhost:8000';
const PAYMENT   = 'http://localhost:8001';

function App() {
  // ── State ──────────────────────────────────
  const [tab, setTab]               = useState('products');      // active tab
  const [products, setProducts]     = useState([]);              // product list from Inventory
  const [orders, setOrders]         = useState([]);              // orders placed this session
  const [loadingProducts, setLoadingProducts] = useState(false);
  const [orderModal, setOrderModal] = useState(null);            // product currently being ordered (or null)
  const [orderQty, setOrderQty]     = useState(1);               // quantity chosen in the modal
  const [showAddForm, setShowAddForm] = useState(false);         // toggle the add-product form
  const [newProduct, setNewProduct] = useState({ name: '', price: '', quantity: '' });
  const [toast, setToast]           = useState(null);            // { message, type } notification

  // ── Helpers ────────────────────────────────

  // Show a temporary toast notification (disappears after 3 s)
  const notify = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  // ── Data fetching ──────────────────────────

  // Fetch all products from the Inventory service
  const fetchProducts = useCallback(async () => {
    setLoadingProducts(true);
    try {
      const res = await fetch(`${INVENTORY}/products`);
      setProducts(await res.json());
    } catch {
      notify('Cannot reach inventory service (port 8000).', 'error');
    } finally {
      setLoadingProducts(false);
    }
  }, []);

  // Load products once on mount
  useEffect(() => { fetchProducts(); }, [fetchProducts]);

  // Auto-poll pending orders every 3 s.
  // When all orders are settled (completed/refunded) the interval is cleared.
  useEffect(() => {
    if (!orders.some(o => o.status === 'pending')) return;

    const id = setInterval(async () => {
      // Re-fetch every order by its pk from the Payment service
      const updated = await Promise.all(
        orders.map(o => fetch(`${PAYMENT}/orders/${o.pk}`).then(r => r.json()))
      );
      setOrders(updated);

      // Refresh product stock whenever an order just completed
      if (updated.some(o => o.status === 'completed')) fetchProducts();
    }, 3000);

    return () => clearInterval(id); // cleanup when orders list changes
  }, [orders, fetchProducts]);

  // ── Actions ────────────────────────────────

  // POST /orders to the Payment service with the selected product id and quantity
  const placeOrder = async () => {
    try {
      const res = await fetch(`${PAYMENT}/orders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: orderModal.id, quantity: parseInt(orderQty) }),
      });
      if (!res.ok) throw new Error();
      const order = await res.json();
      setOrders(prev => [order, ...prev]); // prepend so newest order is first
      setOrderModal(null);
      setTab('orders');
      notify('Order placed! Watching for status update…');
    } catch {
      notify('Failed to place order.', 'error');
    }
  };

  // POST /products to the Inventory service to create a new product
  const addProduct = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${INVENTORY}/products`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name:     newProduct.name,
          price:    parseFloat(newProduct.price),
          quantity: parseInt(newProduct.quantity),
        }),
      });
      if (!res.ok) throw new Error();
      setNewProduct({ name: '', price: '', quantity: '' });
      setShowAddForm(false);
      fetchProducts();
      notify('Product added.');
    } catch {
      notify('Failed to add product.', 'error');
    }
  };

  // DELETE /products/{id} from the Inventory service
  const deleteProduct = async (id) => {
    try {
      await fetch(`${INVENTORY}/products/${id}`, { method: 'DELETE' });
      fetchProducts();
      notify('Product deleted.');
    } catch {
      notify('Failed to delete product.', 'error');
    }
  };

  // Pre-calculate order totals to display in the modal summary
  const subtotal = orderModal ? orderModal.price * orderQty : 0;

  // ── Render ─────────────────────────────────
  return (
    <div className="app">

      {/* Toast notification – shown briefly after each action */}
      {toast && <div className={`toast toast-${toast.type}`}>{toast.message}</div>}

      {/* ── Header / Nav ── */}
      <header className="header">
        <span className="logo">🛍 Microservice Shop</span>
        <nav>
          <button className={tab === 'products' ? 'nav-btn active' : 'nav-btn'} onClick={() => setTab('products')}>
            Products {products.length > 0 && <span className="badge">{products.length}</span>}
          </button>
          <button className={tab === 'orders' ? 'nav-btn active' : 'nav-btn'} onClick={() => setTab('orders')}>
            Orders {orders.length > 0 && <span className="badge">{orders.length}</span>}
          </button>
        </nav>
      </header>

      <main className="main">

        {/* ══ PRODUCTS TAB ══════════════════════════ */}
        {tab === 'products' && (
          <>
            <div className="row-between">
              <h2>Products</h2>
              <div className="row-gap">
                <button className="btn-ghost" onClick={fetchProducts}>Refresh</button>
                <button className="btn-primary" onClick={() => setShowAddForm(v => !v)}>
                  {showAddForm ? 'Cancel' : '+ Add Product'}
                </button>
              </div>
            </div>

            {/* Add-product inline form */}
            {showAddForm && (
              <form className="add-form" onSubmit={addProduct}>
                <p className="form-title">New Product</p>
                <div className="form-row">
                  <input placeholder="Name" value={newProduct.name}
                    onChange={e => setNewProduct({ ...newProduct, name: e.target.value })} required />
                  <input type="number" placeholder="Price" min="0" step="0.01" value={newProduct.price}
                    onChange={e => setNewProduct({ ...newProduct, price: e.target.value })} required />
                  <input type="number" placeholder="Quantity" min="1" value={newProduct.quantity}
                    onChange={e => setNewProduct({ ...newProduct, quantity: e.target.value })} required />
                  <button type="submit" className="btn-primary">Add</button>
                </div>
              </form>
            )}

            {/* Product cards grid */}
            {loadingProducts
              ? <p className="muted center">Loading products…</p>
              : products.length === 0
                ? <p className="muted center">No products yet. Add one above.</p>
                : (
                  <div className="grid">
                    {products.map(p => (
                      <div className="card" key={p.id}>
                        <div className="card-top">
                          <h3 className="product-name">{p.name}</h3>
                          <button className="btn-delete" onClick={() => deleteProduct(p.id)} title="Delete">×</button>
                        </div>
                        <div className="card-mid">
                          <span className="price">${parseFloat(p.price).toFixed(2)}</span>
                          <span className={`stock-pill ${p.quantity === 0 ? 'out' : ''}`}>
                            {p.quantity === 0 ? 'Out of stock' : `${p.quantity} in stock`}
                          </span>
                        </div>
                        {/* Disabled when quantity reaches 0 */}
                        <button
                          className="btn-order"
                          disabled={p.quantity === 0}
                          onClick={() => { setOrderModal(p); setOrderQty(1); }}
                        >
                          {p.quantity === 0 ? 'Out of Stock' : 'Place Order'}
                        </button>
                      </div>
                    ))}
                  </div>
                )
            }
          </>
        )}

        {/* ══ ORDERS TAB ════════════════════════════ */}
        {tab === 'orders' && (
          <>
            <div className="row-between">
              <h2>Orders</h2>
            </div>

            {orders.length === 0
              ? <p className="muted center">No orders yet. Go to Products to place one.</p>
              : (
                <div className="orders-list">
                  {orders.map(o => (
                    <div className="order-card" key={o.pk}>
                      <div className="order-header">
                        {/* Show last 10 chars of the pk as a short reference */}
                        <span className="order-id">#{o.pk?.slice(-10)}</span>
                        <span className={`status-pill status-${o.status}`}>{o.status}</span>
                      </div>
                      <div className="order-grid">
                        <div className="order-field"><label>Qty</label><span>{o.quantity}</span></div>
                        <div className="order-field"><label>Price</label><span>${parseFloat(o.price).toFixed(2)}</span></div>
                        <div className="order-field"><label>Fee (20%)</label><span>${parseFloat(o.fee).toFixed(2)}</span></div>
                        <div className="order-field"><label>Total</label><span className="order-total">${parseFloat(o.total).toFixed(2)}</span></div>
                      </div>
                      {/* Inform the user that the status will update on its own */}
                      {o.status === 'pending' && (
                        <p className="pending-note">⏳ Processing — will update automatically in ~5 seconds.</p>
                      )}
                    </div>
                  ))}
                </div>
              )
            }
          </>
        )}
      </main>

      {/* ══ ORDER MODAL ═══════════════════════════ */}
      {/* Shown when the user clicks "Place Order" on a product card */}
      {orderModal && (
        <div className="overlay" onClick={() => setOrderModal(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>{orderModal.name}</h3>
            <p className="modal-unit">${parseFloat(orderModal.price).toFixed(2)} each</p>

            <label className="modal-label">Quantity</label>
            <input
              className="modal-input"
              type="number"
              min="1"
              max={orderModal.quantity}   // cap at available stock
              value={orderQty}
              onChange={e => setOrderQty(e.target.value)}
            />

            {/* Live price breakdown recalculated as quantity changes */}
            <div className="summary">
              <div className="summary-row"><span>Subtotal</span><span>${subtotal.toFixed(2)}</span></div>
              <div className="summary-row"><span>Fee (20%)</span><span>${(subtotal * 0.2).toFixed(2)}</span></div>
              <div className="summary-row summary-total"><span>Total</span><span>${(subtotal * 1.2).toFixed(2)}</span></div>
            </div>

            <div className="modal-actions">
              <button className="btn-ghost" onClick={() => setOrderModal(null)}>Cancel</button>
              <button className="btn-primary" onClick={placeOrder}>Confirm Order</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
