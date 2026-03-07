/* ============================================================
   SAP Warehouse Copilot — Dashboard JavaScript
   Handles: chat I/O, state polling, robot animations, KPI updates
   ============================================================ */

const API_BASE = window.location.origin;
let isProcessing = false;
let pollInterval = null;

// ---- Chat ----

function sendMessage() {
    const input = document.getElementById('chatInput');
    const text = input.value.trim();
    if (!text || isProcessing) return;

    addMessage('user', text);
    input.value = '';
    setProcessing(true);
    setRobotState('thinking');

    // Send to backend
    fetch(`${API_BASE}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
    })
        .then(res => res.json())
        .then(() => {
            // Start polling for response
            showTypingIndicator();
            pollForResponse();
        })
        .catch(err => {
            addMessage('bot', `Connection error: ${err.message}. Make sure the app is running on Reachy Mini.`);
            setProcessing(false);
            setRobotState('idle');
        });
}

function quickQuery(text) {
    document.getElementById('chatInput').value = text;
    sendMessage();
}

function pollForResponse() {
    let attempts = 0;
    const maxAttempts = 60; // 30 seconds

    const check = () => {
        fetch(`${API_BASE}/api/state`)
            .then(res => res.json())
            .then(data => {
                if (data.state === 'idle' && data.last_response && attempts > 2) {
                    // Response is ready
                    removeTypingIndicator();
                    addMessage('bot', data.last_response);
                    updateKPIs(data.last_metadata);
                    updateToolLog(data.last_metadata);
                    animateRobotForHealth(data.last_metadata);
                    setProcessing(false);
                    setRobotState('idle');
                } else if (attempts < maxAttempts) {
                    attempts++;
                    updateRobotStateFromAPI(data.state);
                    setTimeout(check, 500);
                } else {
                    removeTypingIndicator();
                    addMessage('bot', 'Request timed out. Please try again.');
                    setProcessing(false);
                    setRobotState('idle');
                }
            })
            .catch(() => {
                // If backend not available, simulate response
                removeTypingIndicator();
                simulateResponse(document.getElementById('chatInput').dataset.lastQuery || '');
                setProcessing(false);
                setRobotState('idle');
            });
    };

    // Store last query for fallback
    const msgs = document.querySelectorAll('.msg-user .msg-content');
    if (msgs.length > 0) {
        document.getElementById('chatInput').dataset.lastQuery = msgs[msgs.length - 1].textContent;
    }

    setTimeout(check, 1000);
}

// ---- Simulated responses (when backend unavailable — demo mode) ----

function simulateResponse(query) {
    const q = query.toLowerCase();
    let response = '';
    let metadata = {};

    if (q.includes('warehouse') && (q.includes('status') || q.includes('summary'))) {
        response = `📊 **Warehouse Summary:**\n\n• **6 materials** tracked across 2 plants\n• **2 healthy**, 1 needs reorder, 2 critical, 1 out of stock\n• **1 overdue PO** (4500012003 — Conveyor Belt from FlexLink AB, 2 days late)\n• **3 open maintenance orders** (1 critical — conveyor belt motor replacement)\n\nOverall status: 🔴 **RED** — Immediate attention needed on MAT-1006 (zero stock) and the overdue delivery.`;
        metadata = { stock_health: 'RED', has_overdue: true, tool_calls: [{ name: 'get_warehouse_summary', args: {}, result: { total_materials: 6, healthy: 2, reorder_needed: 1, critical: 2, out_of_stock: 1, overdue_purchase_orders: 1, overall_health: 'RED' } }] };
    } else if (q.includes('overdue')) {
        response = `⚠️ **Overdue Purchase Orders:**\n\nPO **4500012003** — Conveyor Belt Module CBM-3000 (MAT-1006)\n• Vendor: FlexLink AB\n• Quantity: 10 EA @ €2,800.00 each\n• Due: 2 days ago\n• Status: **Overdue**\n\nThis is critical because MAT-1006 is currently **OUT OF STOCK**. I recommend immediate action — contact FlexLink AB for an ETA.`;
        metadata = { has_overdue: true, tool_calls: [{ name: 'get_purchase_orders', args: { status: 'Overdue' }, result: [{ po_number: '4500012003', material: 'MAT-1006', vendor: 'FlexLink AB', status: 'Overdue' }] }] };
    } else if (q.includes('stock') || q.includes('inventory') || q.includes('pump') || q.includes('mat-')) {
        const mat = q.includes('pump') ? 'MAT-1001' : q.includes('motor') || q.includes('servo') ? 'MAT-1002' : q.includes('bearing') ? 'MAT-1003' : q.includes('plc') ? 'MAT-1005' : q.includes('conveyor') || q.includes('1006') ? 'MAT-1006' : 'MAT-1001';
        const stocks = {
            'MAT-1001': { desc: 'Hydraulic Pump Assembly HPA-200', avail: 34, health: 'HEALTHY', unrestricted: 42, reserved: 8 },
            'MAT-1002': { desc: 'Servo Motor Drive Unit SMD-X7', avail: 2, health: 'CRITICAL', unrestricted: 7, reserved: 5 },
            'MAT-1003': { desc: 'Industrial Bearing SKF-6205', avail: 900, health: 'HEALTHY', unrestricted: 1200, reserved: 300 },
            'MAT-1005': { desc: 'PLC Controller Siemens S7-1500', avail: 16, health: 'HEALTHY', unrestricted: 18, reserved: 2 },
            'MAT-1006': { desc: 'Conveyor Belt Module CBM-3000', avail: 0, health: 'OUT_OF_STOCK', unrestricted: 0, reserved: 0 },
        };
        const s = stocks[mat] || stocks['MAT-1001'];
        const emoji = s.health === 'HEALTHY' ? '✅' : s.health === 'CRITICAL' ? '🔴' : s.health === 'OUT_OF_STOCK' ? '⛔' : '🟡';
        response = `${emoji} **${mat} — ${s.desc}**\n\n• Unrestricted: ${s.unrestricted} EA\n• Reserved: ${s.reserved} EA\n• Available: **${s.avail} EA**\n• Status: **${s.health}**${s.health === 'OUT_OF_STOCK' ? '\n\n⚠️ Zero stock! There is a pending PO (4500012003) that is overdue. I recommend immediate action.' : s.health === 'CRITICAL' ? '\n\n⚠️ Below safety stock. A PO is in transit — check delivery status.' : ''}`;
        metadata = { stock_health: s.health, tool_calls: [{ name: 'get_stock_level', args: { material_id: mat }, result: { material_number: mat, available: s.avail, health: s.health } }] };
    } else if (q.includes('maintenance') || q.includes('work order')) {
        response = `🔧 **Open Maintenance Orders:**\n\n1. **800010001** — Quarterly inspection, Pump Station Alpha\n   Priority: High | Status: In Process\n\n2. **800010002** — Replace conveyor belt motor, Line 3\n   Priority: 🔴 Critical | Status: Released\n\n3. **800010003** — Calibrate PLC sensors, Cell B\n   Priority: Medium | Status: Scheduled\n\nThe conveyor belt motor replacement (800010002) is critical and should be prioritized today.`;
        metadata = { tool_calls: [{ name: 'get_maintenance_orders', args: {}, result: [] }] };
    } else if (q.includes('reorder') || q.includes('needs ordering')) {
        response = `📦 **Materials needing reorder:**\n\n1. **MAT-1002** — Servo Motor Drive Unit SMD-X7\n   Available: 2 EA (Safety stock: 8) — 🔴 CRITICAL\n   PO 4500012001 for 50 EA arriving in 3 days\n\n2. **MAT-1004** — Stainless Steel Flange DN50\n   Available: 0 EA (blocked: 2) — 🔴 CRITICAL\n   PO 4500012002 for 100 EA arriving in 7 days\n\n3. **MAT-1006** — Conveyor Belt Module CBM-3000\n   Available: 0 EA — ⛔ OUT OF STOCK\n   PO 4500012003 is OVERDUE`;
        metadata = { stock_health: 'RED', has_overdue: true, tool_calls: [{ name: 'get_warehouse_summary', args: {}, result: {} }] };
    } else {
        response = `I can help you with SAP warehouse queries! Try asking about:\n\n• **Stock levels** — "Check stock for hydraulic pump"\n• **Purchase orders** — "Show overdue POs"\n• **Maintenance** — "Any critical maintenance orders?"\n• **Overview** — "What's the warehouse status?"`;
        metadata = {};
    }

    addMessage('bot', response);
    updateKPIs(metadata);
    updateToolLog(metadata);
    animateRobotForHealth(metadata);
}

// ---- UI Helpers ----

function addMessage(role, content) {
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.className = `msg msg-${role === 'user' ? 'user' : 'bot'}`;

    const avatar = role === 'user' ? '👤' : '🤖';
    const html = content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>');

    div.innerHTML = `
        <div class="msg-avatar">${avatar}</div>
        <div class="msg-content">${html}</div>
    `;

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function showTypingIndicator() {
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.className = 'msg msg-bot';
    div.id = 'typingMsg';
    div.innerHTML = `
        <div class="msg-avatar">🤖</div>
        <div class="typing-indicator"><span></span><span></span><span></span></div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function removeTypingIndicator() {
    const el = document.getElementById('typingMsg');
    if (el) el.remove();
}

function setProcessing(val) {
    isProcessing = val;
    document.getElementById('btnSend').disabled = val;
}

function setRobotState(state) {
    const viz = document.getElementById('robotViz');
    const label = document.getElementById('robotStateLabel');
    const badge = document.getElementById('statusBadge');

    viz.className = 'robot-viz';

    const stateMap = {
        idle: { cls: 'robot-idle', label: 'Idle — Waiting for input', badgeCls: '', badgeText: 'Idle' },
        listening: { cls: 'robot-listening', label: 'Listening — Capturing speech', badgeCls: 'listening', badgeText: 'Listening' },
        thinking: { cls: 'robot-thinking', label: 'Thinking — Querying SAP via NIM', badgeCls: 'thinking', badgeText: 'Processing' },
        speaking: { cls: 'robot-speaking', label: 'Speaking — Delivering response', badgeCls: 'speaking', badgeText: 'Speaking' },
    };

    const s = stateMap[state] || stateMap.idle;
    viz.classList.add(s.cls);
    label.textContent = s.label;
    badge.className = `status-badge ${s.badgeCls}`;
    badge.querySelector('.status-text').textContent = s.badgeText;
}

function updateRobotStateFromAPI(apiState) {
    if (apiState === 'thinking') setRobotState('thinking');
    else if (apiState === 'listening') setRobotState('listening');
    else if (apiState === 'speaking') setRobotState('speaking');
}

function animateRobotForHealth(metadata) {
    const viz = document.getElementById('robotViz');
    const health = metadata?.stock_health;
    const overdue = metadata?.has_overdue;

    viz.className = 'robot-viz';

    if (health === 'OUT_OF_STOCK' || health === 'CRITICAL' || health === 'RED' || overdue) {
        viz.classList.add('robot-alert');
        setTimeout(() => {
            viz.className = 'robot-viz robot-idle';
        }, 3000);
    } else {
        viz.classList.add('robot-idle');
    }
}

function updateKPIs(metadata) {
    const tc = metadata?.tool_calls || [];
    for (const call of tc) {
        if (call.name === 'get_warehouse_summary' && call.result) {
            const r = call.result;
            setKPI('kpiHealthy', r.healthy);
            setKPI('kpiReorder', r.reorder_needed);
            setKPI('kpiCritical', r.critical);
            setKPI('kpiOutOfStock', r.out_of_stock);
        }
    }
}

function setKPI(id, value) {
    if (value !== undefined && value !== null) {
        document.getElementById(id).querySelector('.kpi-value').textContent = value;
    }
}

function updateToolLog(metadata) {
    const log = document.getElementById('toolLog');
    const tc = metadata?.tool_calls || [];

    if (tc.length === 0) return;

    // Clear "no queries" message
    const empty = log.querySelector('.tool-empty');
    if (empty) empty.remove();

    for (const call of tc) {
        const entry = document.createElement('div');
        entry.className = 'tool-entry';
        const argsStr = JSON.stringify(call.args || {});
        const resultPreview = typeof call.result === 'object'
            ? JSON.stringify(call.result).substring(0, 80) + '...'
            : String(call.result).substring(0, 80);
        entry.innerHTML = `
            <div><span class="tool-name">${call.name}</span>(<span class="tool-args">${argsStr}</span>)</div>
            <div class="tool-result">→ ${resultPreview}</div>
        `;
        log.prepend(entry);
    }
}

function resetConversation() {
    fetch(`${API_BASE}/api/reset`, { method: 'POST' }).catch(() => {});

    document.getElementById('chatMessages').innerHTML = `
        <div class="msg msg-bot">
            <div class="msg-avatar">🤖</div>
            <div class="msg-content">
                <p>Conversation reset! I'm your <strong>SAP Warehouse Copilot</strong>, ready for queries.</p>
            </div>
        </div>
    `;
    document.getElementById('toolLog').innerHTML = '<p class="tool-empty">No SAP queries yet. Ask something!</p>';

    ['kpiHealthy', 'kpiReorder', 'kpiCritical', 'kpiOutOfStock'].forEach(id => setKPI(id, '—'));

    setRobotState('idle');
}

// ---- Init ----
document.addEventListener('DOMContentLoaded', () => {
    setRobotState('idle');

    // Auto-load warehouse summary KPIs
    setTimeout(() => {
        fetch(`${API_BASE}/api/state`).catch(() => {
            // Backend not available — that's fine, we're in demo mode
            console.log('SAP Warehouse Copilot: Running in demo mode (no backend)');
        });
    }, 1000);
});
