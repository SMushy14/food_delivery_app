// Global variables
let currentOrder = {
    stallId: null,
    items: [],
    total: 0
};

// Add item to order
function addToOrder(e) {
    const itemId = e.target.dataset.id;
    const itemName = e.target.dataset.name;
    const itemPrice = parseFloat(e.target.dataset.price);
    
    // Check if item already in order
    const existingItem = currentOrder.items.find(item => item.id === itemId);
    if (existingItem) {
        existingItem.quantity += 1;
    } else {
        currentOrder.items.push({
            id: itemId,
            name: itemName,
            price: itemPrice,
            quantity: 1
        });
    }
    
    currentOrder.total += itemPrice;
    updateOrderSummary();
}

// Update order summary
function updateOrderSummary() {
    const orderItemsContainer = document.getElementById('orderItems');
    orderItemsContainer.innerHTML = '';
    
    currentOrder.items.forEach(item => {
        const orderItem = document.createElement('div');
        orderItem.innerHTML = `
            <span>${item.name} x${item.quantity}</span>
            <span>$${(item.price * item.quantity).toFixed(2)}</span>
        `;
        orderItemsContainer.appendChild(orderItem);
    });
    
    document.getElementById('orderTotal').textContent = `Total: $${currentOrder.total.toFixed(2)}`;
}

// Place order
function placeOrder() {
    if (currentOrder.items.length === 0) return;
    
    fetch('/api/orders', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            stallId: currentOrder.stallId,
            items: currentOrder.items.map(item => ({
                id: item.id,
                name: item.name,
                price: item.price,
                quantity: item.quantity
            })),
            total: currentOrder.total
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
            return;
        }
        
        // Show confirmation
        document.getElementById('orderId').textContent = data.order_id;
        document.getElementById('menuModal').style.display = 'none';
        document.getElementById('orderConfirmation').style.display = 'block';
        
        // Reset current order
        currentOrder = {
            stallId: null,
            items: [],
            total: 0
        };
    });
}

// Modal functions
function setupModalCloseHandlers() {
    // Close buttons
    document.querySelectorAll('.close-btn, #confirmOkBtn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.modal').forEach(modal => {
                modal.style.display = 'none';
            });
        });
    });
    
    // Close when clicking outside modal content
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            e.target.style.display = 'none';
        }
    });
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupModalCloseHandlers();
    
    // Place order button
    const placeOrderBtn = document.getElementById('placeOrderBtn');
    if (placeOrderBtn) {
        placeOrderBtn.addEventListener('click', placeOrder);
    }
    
    // Add event listeners to menu items (added dynamically)
    document.addEventListener('click', function(e) {
        if (e.target.matches('#menuItemsContainer button')) {
            addToOrder(e);
        }
    });
});
