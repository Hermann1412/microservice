# Microservice Shop – Frontend

React frontend for the microservice project. Connects to two backend services:

| Service | URL |
|---------|-----|
| Inventory API | `http://localhost:8000` |
| Payment API | `http://localhost:8001` |

---

## Getting Started

```bash
npm install   # only needed once
npm start     # opens http://localhost:3000
```

Make sure both backend services are running before you open the app.

---

## Features

### Products tab
- Lists all products fetched from the Inventory service
- **Add Product** — inline form to create a new product (name, price, quantity)
- **Delete** — removes a product from inventory
- **Place Order** — opens the order modal (button disabled when stock is 0)

### Order modal
- Choose the quantity you want to buy
- Live price breakdown: subtotal, 20% fee, total
- Click **Confirm Order** to send the request to the Payment service

### Orders tab
- Shows every order placed during the current session
- Status badge: `pending` → `completed` (or `refunded`)
- **Auto-polls every 3 seconds** while any order is still `pending` — no manual refresh needed
- When an order completes, the product stock is refreshed automatically

---

## How an order works (end-to-end)

```
User clicks "Confirm Order"
        │
        ▼
POST /orders  →  Payment API (port 8001)
        │  returns order with status "pending"
        │
        ▼  (background task, ~5 seconds)
Payment API marks order "completed"
        │
        ▼  publishes to Redis Stream "order_completed"
        │
        ▼
Inventory Consumer reads event
        │  decrements product quantity
        ▼
Frontend polls GET /orders/{pk}  →  status flips to "completed"
```

---

## Project Structure

```
src/
├── App.js      # All components and logic (state, API calls, rendering)
└── App.css     # All styles
```

Everything lives in `App.js` for simplicity. Key sections inside the file:

| Section | What it does |
|---------|-------------|
| Constants `INVENTORY`, `PAYMENT` | Base URLs — change these if your ports differ |
| `fetchProducts` | `GET /products` from Inventory, called on mount and after mutations |
| `useEffect` (polling) | Watches `orders` state; polls every 3 s while any order is `pending` |
| `placeOrder` | `POST /orders` to Payment with `{ id, quantity }` |
| `addProduct` | `POST /products` to Inventory |
| `deleteProduct` | `DELETE /products/{id}` from Inventory |
| Products tab JSX | Grid of product cards |
| Orders tab JSX | List of order cards with live status badges |
| Order modal JSX | Quantity picker + price summary |

---

## Updating the UI

**Add a new page / tab**
1. Add a new value to the `tab` state (e.g. `'reports'`)
2. Add a nav button in the `<header>` section
3. Add a `{tab === 'reports' && (...)}` block inside `<main>`

**Add a new API field**
- Backend model changes are reflected automatically as long as the field
  is returned in the JSON response. Just reference `product.newField` or
  `order.newField` in the JSX.

**Change backend URLs**
- Edit the `INVENTORY` and `PAYMENT` constants at the top of `App.js`

**Styling**
- All styles are in `App.css` — class names match the JSX directly
- Responsive breakpoint at 600 px (order grid collapses to 2 columns)

---

## Available Scripts

| Command | Description |
|---------|-------------|
| `npm start` | Development server at `http://localhost:3000` with hot reload |
| `npm run build` | Production build output to `build/` folder |
| `npm test` | Run tests with Jest |
