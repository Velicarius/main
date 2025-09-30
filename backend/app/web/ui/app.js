// Global state
let positions = [];
let filteredPositions = [];
let backendUrl = '';
let demoUserId = '';

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    const backendInput = document.getElementById('backend-url');
    const filterInput = document.getElementById('filter');
    
    // Set default backend URL from environment or fallback
    // VITE_API_URL is injected at build time, but we'll use a runtime approach
    const envApiUrl = window.VITE_API_URL || 'http://localhost:8001';
    backendUrl = envApiUrl;
    backendInput.value = backendUrl;

    // Pick up demo user id if provided
    demoUserId = window.VITE_DEMO_USER_ID || '';

    // Update backend URL when input changes
    backendInput.addEventListener('input', function() {
        backendUrl = this.value || window.location.origin;
    });
    
    // Filter positions when filter input changes
    filterInput.addEventListener('input', function() {
        filterPositions();
    });
    
    // Load initial data
    loadPositions();
});

async function loadPositions() {
    const reloadBtn = document.getElementById('reload-btn');
    const errorDiv = document.getElementById('error');
    
    try {
        reloadBtn.disabled = true;
        reloadBtn.textContent = 'Loading...';
        errorDiv.style.display = 'none';
        
        // Fetch positions
        let url = `${backendUrl}/positions`;
        if (demoUserId) {
            url += `?user_id=${encodeURIComponent(demoUserId)}`;
        }
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`Failed to load positions: ${response.status}`);
        }
        
        positions = await response.json();
        
        // Fetch latest prices for each position
        const enrichedPositions = await Promise.all(
            positions.map(async (pos) => {
                try {
                    const priceResponse = await fetch(`${backendUrl}/prices-eod/${encodeURIComponent(pos.symbol)}/latest`);
                    let latestPrice = null;
                    
                    if (priceResponse.ok) {
                        latestPrice = await priceResponse.json();
                    } else if (priceResponse.status !== 404) {
                        console.warn(`Failed to fetch price for ${pos.symbol}: ${priceResponse.status}`);
                    }
                    
                    const last = latestPrice?.close ?? null;
                    const lastDate = latestPrice?.date ?? null;
                    const value = last != null ? last * pos.quantity : null;
                    const pnl = last != null && pos.buy_price != null ? (last - pos.buy_price) * pos.quantity : null;
                    
                    return {
                        ...pos,
                        last,
                        lastDate,
                        value,
                        pnl
                    };
                } catch (error) {
                    console.warn(`Error fetching price for ${pos.symbol}:`, error);
                    return {
                        ...pos,
                        last: null,
                        lastDate: null,
                        value: null,
                        pnl: null
                    };
                }
            })
        );
        
        positions = enrichedPositions;
        filterPositions();
        
    } catch (error) {
        console.error('Error loading positions:', error);
        errorDiv.textContent = error.message;
        errorDiv.style.display = 'block';
    } finally {
        reloadBtn.disabled = false;
        reloadBtn.textContent = 'Reload';
    }
}

function filterPositions() {
    const filterValue = document.getElementById('filter').value.trim().toLowerCase();
    
    if (!filterValue) {
        filteredPositions = positions;
    } else {
        filteredPositions = positions.filter(pos => 
            pos.symbol.toLowerCase().includes(filterValue) ||
            (pos.account || '').toLowerCase().includes(filterValue)
        );
    }
    
    renderTable();
    updateTotals();
}

function renderTable() {
    const tbody = document.getElementById('positions-table');
    
    if (filteredPositions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="center muted">No positions found</td></tr>';
        return;
    }
    
    tbody.innerHTML = filteredPositions.map(pos => `
        <tr>
            <td>${pos.symbol}</td>
            <td class="right">${pos.quantity}</td>
            <td class="right">${pos.buy_price != null ? pos.buy_price.toLocaleString() : '—'}</td>
            <td class="right">${pos.last != null ? pos.last.toLocaleString() : '<span class="muted">—</span>'}</td>
            <td class="muted">${pos.lastDate || ''}</td>
            <td class="right">${pos.value != null ? pos.value.toLocaleString() : '<span class="muted">—</span>'}</td>
            <td class="right ${pos.pnl != null ? (pos.pnl >= 0 ? 'pos' : 'neg') : ''}">${pos.pnl != null ? pos.pnl.toLocaleString() : '<span class="muted">—</span>'}</td>
            <td class="muted">${pos.account || ''}</td>
        </tr>
    `).join('');
}

function updateTotals() {
    const totalValue = filteredPositions.reduce((sum, pos) => sum + (pos.value || 0), 0);
    const totalPnL = filteredPositions.reduce((sum, pos) => sum + (pos.pnl || 0), 0);
    
    document.getElementById('total-value').textContent = totalValue.toLocaleString();
    
    const pnlElement = document.getElementById('total-pnl');
    pnlElement.textContent = totalPnL.toLocaleString();
    pnlElement.className = totalPnL >= 0 ? 'pos' : 'neg';
}

async function triggerEOD() {
    const triggerBtn = document.getElementById('trigger-btn');
    const sinceInput = document.getElementById('since-date');
    const errorDiv = document.getElementById('error');
    
    try {
        triggerBtn.disabled = true;
        triggerBtn.textContent = 'Queuing...';
        errorDiv.style.display = 'none';
        
        const body = {};
        if (positions.length > 0) {
            body.symbols = positions.map(pos => pos.symbol);
        }
        if (sinceInput.value) {
            body.since = sinceInput.value;
        }
        
        const response = await fetch(`${backendUrl}/admin/tasks/fetch-eod`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(body)
        });
        
        if (!response.ok) {
            throw new Error(`Failed to trigger EOD: ${response.status}`);
        }
        
        const result = await response.json();
        const message = `EOD task queued${result.task_id ? ` (ID: ${result.task_id})` : ''}`;
        alert(message);
        
    } catch (error) {
        console.error('Error triggering EOD:', error);
        errorDiv.textContent = error.message;
        errorDiv.style.display = 'block';
    } finally {
        triggerBtn.disabled = false;
        triggerBtn.textContent = 'Trigger EOD task';
    }
}
