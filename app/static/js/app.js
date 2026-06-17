/**
 * Web Tool Set - Frontend Application
 */

// API base URL
const API_BASE = '/api';

// Theme management
const ThemeManager = {
    init() {
        // Check for saved theme preference or use system preference
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            document.documentElement.setAttribute('data-theme', savedTheme);
        }
        
        // Theme toggle button
        const themeToggle = document.getElementById('theme-toggle');
        themeToggle?.addEventListener('click', () => this.toggle());
    },

    toggle() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        
        let newTheme;
        if (currentTheme === 'dark') {
            newTheme = 'light';
        } else if (currentTheme === 'light') {
            newTheme = 'dark';
        } else {
            // No manual theme set, toggle from system preference
            newTheme = prefersDark ? 'light' : 'dark';
        }
        
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
    }
};

// Tab management
const TabManager = {
    init() {
        const tabBtns = document.querySelectorAll('.tab-btn');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => this.switchTab(btn.dataset.tab));
        });
    },

    switchTab(tabId) {
        // Update button states
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabId);
        });
        
        // Update content visibility
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('active', content.id === `${tabId}-tab`);
        });
    }
};

// Toast notifications
const Toast = {
    show(message, type = 'success', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
};

// API utilities
const API = {
    async get(endpoint) {
        const response = await fetch(`${API_BASE}${endpoint}`);
        const data = await response.json();
        return { ok: response.ok, status: response.status, data };
    },

    async ping(address = '') {
        const url = address ? `/ping/${encodeURIComponent(address)}` : '/ping';
        return this.get(url);
    },

    async tcping(address = '', port = 80, timeout = 2) {
        let url = '/tcping';
        const params = new URLSearchParams();
        
        if (address) {
            url = `/tcping/${encodeURIComponent(address)}`;
        }
        if (port !== 80) params.set('port', port);
        if (timeout !== 2) params.set('timeout', timeout);
        
        const queryString = params.toString();
        return this.get(url + (queryString ? `?${queryString}` : ''));
    },

    async nslookup(address) {
        return this.get(`/nslookup/${encodeURIComponent(address)}`);
    },

    async dig(address, type = 'A') {
        const params = new URLSearchParams();
        if (type && type !== 'A') params.set('type', type);
        const queryString = params.toString();
        return this.get(`/dig/${encodeURIComponent(address)}` + (queryString ? `?${queryString}` : ''));
    },

    async reverseIp(address = '') {
        const url = address ? `/reverse-ip/${encodeURIComponent(address)}` : '/reverse-ip';
        return this.get(url);
    },

    async traceroute(address, maxHops = 30, timeout = 2) {
        const params = new URLSearchParams();
        if (maxHops !== 30) params.set('max_hops', maxHops);
        if (timeout !== 2) params.set('timeout', timeout);
        const queryString = params.toString();
        return this.get(`/traceroute/${encodeURIComponent(address)}` + (queryString ? `?${queryString}` : ''));
    },

    async whois(query) {
        return this.get(`/whois/${encodeURIComponent(query)}`);
    },

    async wol(macAddress) {
        return this.get(`/wol/${encodeURIComponent(macAddress)}`);
    },

    async portCheck(address, port, timeout = 3) {
        const params = new URLSearchParams();
        if (timeout !== 3) params.set('timeout', timeout);
        const queryString = params.toString();
        return this.get(`/port/${encodeURIComponent(address)}/${port}` + (queryString ? `?${queryString}` : ''));
    },

    async getMyIp() {
        return this.get('/myip');
    }
};

// UI Helpers
function formatDelay(ms) {
    if (ms === null || ms === undefined) return 'N/A';
    return `${ms.toFixed(2)} ms`;
}

function showResult(containerId, content) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const contentDiv = container.querySelector('.result-content');
    if (contentDiv) {
        contentDiv.innerHTML = content;
    }
    container.classList.remove('hidden');
}

function hideResult(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.classList.add('hidden');
    }
}

function setButtonLoading(form, loading) {
    const btn = form.querySelector('.btn-primary');
    const btnText = btn.querySelector('.btn-text');
    const btnLoading = btn.querySelector('.btn-loading');
    
    btn.disabled = loading;
    btnText.classList.toggle('hidden', loading);
    btnLoading.classList.toggle('hidden', !loading);
}

// Tool handlers
const PingTool = {
    init() {
        const form = document.getElementById('ping-form');
        form?.addEventListener('submit', (e) => this.handleSubmit(e));
    },

    async handleSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const address = form.address.value.trim();

        setButtonLoading(form, true);
        hideResult('ping-result');

        try {
            const { ok, data } = await API.ping(address);
            
            if (ok && data.delay !== null && data.delay !== undefined) {
                showResult('ping-result', `
                    <div class="result-item">
                        <span class="result-label">Target Address</span>
                        <span class="result-value">${address || 'Local IP'}</span>
                    </div>
                    <div class="result-item">
                        <span class="result-label">Average Latency</span>
                        <span class="result-value success">${formatDelay(data.delay)}</span>
                    </div>
                `);
                Toast.show('Ping successful!', 'success');
            } else {
                const errorMsg = data.error || 'Unknown error';
                showResult('ping-result', `
                    <div class="result-error">
                        <strong>Error:</strong> ${escapeHtml(errorMsg)}
                    </div>
                `);
                Toast.show('Ping failed', 'error');
            }
        } catch (error) {
            showResult('ping-result', `
                <div class="result-error">
                    <strong>Request failed:</strong> ${escapeHtml(error.message)}
                </div>
            `);
            Toast.show('Request failed', 'error');
        } finally {
            setButtonLoading(form, false);
        }
    }
};

const TcpPingTool = {
    init() {
        const form = document.getElementById('tcping-form');
        form?.addEventListener('submit', (e) => this.handleSubmit(e));
    },

    async handleSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const address = form.address.value.trim();
        const port = parseInt(form.port.value) || 80;
        const timeout = parseInt(form.timeout.value) || 2;

        if (!address) {
            Toast.show('Please enter a target address', 'warning');
            return;
        }

        setButtonLoading(form, true);
        hideResult('tcping-result');

        try {
            const { ok, data } = await API.tcping(address, port, timeout);
            
            if (ok && data.delay !== null && data.delay !== undefined) {
                showResult('tcping-result', `
                    <div class="result-item">
                        <span class="result-label">Target Address</span>
                        <span class="result-value">${escapeHtml(address)}</span>
                    </div>
                    <div class="result-item">
                        <span class="result-label">Port</span>
                        <span class="result-value">${port}</span>
                    </div>
                    <div class="result-item">
                        <span class="result-label">Average Latency</span>
                        <span class="result-value success">${formatDelay(data.delay)}</span>
                    </div>
                `);
                Toast.show('TCP Ping successful!', 'success');
            } else {
                const errorMsg = data.error || 'Unknown error';
                showResult('tcping-result', `
                    <div class="result-error">
                        <strong>Error:</strong> ${escapeHtml(errorMsg)}
                    </div>
                `);
                Toast.show('TCP Ping failed', 'error');
            }
        } catch (error) {
            showResult('tcping-result', `
                <div class="result-error">
                    <strong>Request failed:</strong> ${escapeHtml(error.message)}
                </div>
            `);
            Toast.show('Request failed', 'error');
        } finally {
            setButtonLoading(form, false);
        }
    }
};

const NslookupTool = {
    init() {
        const form = document.getElementById('nslookup-form');
        form?.addEventListener('submit', (e) => this.handleSubmit(e));
    },

    async handleSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const address = form.address.value.trim();

        if (!address) {
            Toast.show('Please enter a target address or domain', 'warning');
            return;
        }

        setButtonLoading(form, true);
        hideResult('nslookup-result');

        try {
            const { ok, data } = await API.nslookup(address);

            if (ok && data.addresses && data.addresses.length > 0) {
                let rows = `
                    <div class="result-item">
                        <span class="result-label">Query Name</span>
                        <span class="result-value">${escapeHtml(data.name)}</span>
                    </div>
                `;
                if (data.server) {
                    rows += `
                    <div class="result-item">
                        <span class="result-label">DNS Server</span>
                        <span class="result-value">${escapeHtml(data.server)}</span>
                    </div>
                    `;
                }
                if (data.canonical_name) {
                    rows += `
                    <div class="result-item">
                        <span class="result-label">Canonical Name</span>
                        <span class="result-value">${escapeHtml(data.canonical_name)}</span>
                    </div>
                    `;
                }
                rows += data.addresses.map(addr => `
                    <div class="result-item">
                        <span class="result-label">Resolved</span>
                        <span class="result-value success">${escapeHtml(addr)}</span>
                    </div>
                `).join('');
                showResult('nslookup-result', rows);
                Toast.show('Resolved successfully!', 'success');
            } else {
                const errorMsg = data.error || 'No records found';
                showResult('nslookup-result', `
                    <div class="result-error">
                        <strong>Error:</strong> ${escapeHtml(errorMsg)}
                    </div>
                `);
                Toast.show('Resolution failed', 'error');
            }
        } catch (error) {
            showResult('nslookup-result', `
                <div class="result-error">
                    <strong>Request failed:</strong> ${escapeHtml(error.message)}
                </div>
            `);
            Toast.show('Request failed', 'error');
        } finally {
            setButtonLoading(form, false);
        }
    }
};

const DigTool = {
    init() {
        const form = document.getElementById('dig-form');
        form?.addEventListener('submit', (e) => this.handleSubmit(e));
    },

    async handleSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const address = form.address.value.trim();
        const type = form.type.value;

        if (!address) {
            Toast.show('Please enter a domain', 'warning');
            return;
        }

        setButtonLoading(form, true);
        hideResult('dig-result');

        try {
            const { ok, data } = await API.dig(address, type);

            if (ok && data.records && data.records.length > 0) {
                let rows = `
                    <div class="result-item">
                        <span class="result-label">Query Name</span>
                        <span class="result-value">${escapeHtml(data.name)} (${escapeHtml(data.record_type)})</span>
                    </div>
                `;
                if (data.server) {
                    rows += `
                    <div class="result-item">
                        <span class="result-label">DNS Server</span>
                        <span class="result-value">${escapeHtml(data.server)}</span>
                    </div>
                    `;
                }
                rows += data.records.map(rec => `
                    <div class="result-item">
                        <span class="result-label">${escapeHtml(rec.type)}${rec.ttl !== null && rec.ttl !== undefined ? ` · TTL ${rec.ttl}s` : ''}</span>
                        <span class="result-value success">${escapeHtml(rec.value)}</span>
                    </div>
                `).join('');
                if (data.query_time !== null && data.query_time !== undefined) {
                    rows += `
                    <div class="result-item">
                        <span class="result-label">Query Time</span>
                        <span class="result-value">${data.query_time.toFixed(2)} ms</span>
                    </div>
                    `;
                }
                showResult('dig-result', rows);
                Toast.show('Query successful!', 'success');
            } else {
                const errorMsg = data.error || 'No records found';
                showResult('dig-result', `
                    <div class="result-error">
                        <strong>Error:</strong> ${escapeHtml(errorMsg)}
                    </div>
                `);
                Toast.show('Query failed', 'error');
            }
        } catch (error) {
            showResult('dig-result', `
                <div class="result-error">
                    <strong>Request failed:</strong> ${escapeHtml(error.message)}
                </div>
            `);
            Toast.show('Request failed', 'error');
        } finally {
            setButtonLoading(form, false);
        }
    }
};

const ReverseIpTool = {
    init() {
        const form = document.getElementById('reverseip-form');
        form?.addEventListener('submit', (e) => this.handleSubmit(e));
    },

    async handleSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const address = form.address.value.trim();

        setButtonLoading(form, true);
        hideResult('reverseip-result');

        try {
            const { ok, data } = await API.reverseIp(address);

            if (ok && data.hostnames && data.hostnames.length > 0) {
                let rows = `
                    <div class="result-item">
                        <span class="result-label">IP Address</span>
                        <span class="result-value">${escapeHtml(data.address)}</span>
                    </div>
                `;
                if (data.server) {
                    rows += `
                    <div class="result-item">
                        <span class="result-label">DNS Server</span>
                        <span class="result-value">${escapeHtml(data.server)}</span>
                    </div>
                    `;
                }
                rows += data.hostnames.map(host => `
                    <div class="result-item">
                        <span class="result-label">Hostname</span>
                        <span class="result-value success">${escapeHtml(host)}</span>
                    </div>
                `).join('');
                showResult('reverseip-result', rows);
                Toast.show('Lookup successful!', 'success');
            } else {
                const errorMsg = data.error || 'No PTR record found';
                showResult('reverseip-result', `
                    <div class="result-error">
                        <strong>Error:</strong> ${escapeHtml(errorMsg)}
                    </div>
                `);
                Toast.show('Lookup failed', 'error');
            }
        } catch (error) {
            showResult('reverseip-result', `
                <div class="result-error">
                    <strong>Request failed:</strong> ${escapeHtml(error.message)}
                </div>
            `);
            Toast.show('Request failed', 'error');
        } finally {
            setButtonLoading(form, false);
        }
    }
};

const TracerouteTool = {
    init() {
        const form = document.getElementById('traceroute-form');
        form?.addEventListener('submit', (e) => this.handleSubmit(e));
    },

    async handleSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const address = form.address.value.trim();
        const maxHops = parseInt(form.max_hops.value) || 30;
        const timeout = parseInt(form.timeout.value) || 2;

        if (!address) {
            Toast.show('Please enter a target address or domain', 'warning');
            return;
        }

        setButtonLoading(form, true);
        hideResult('traceroute-result');

        try {
            const { ok, data } = await API.traceroute(address, maxHops, timeout);

            if (ok && data.hops && data.hops.length > 0) {
                let rows = `
                    <div class="result-item">
                        <span class="result-label">Target Address</span>
                        <span class="result-value">${escapeHtml(data.address)}</span>
                    </div>
                `;
                rows += data.hops.map(hop => {
                    const addr = hop.address || '*';
                    const rtt = hop.is_alive && hop.avg_rtt !== null && hop.avg_rtt !== undefined
                        ? formatDelay(hop.avg_rtt)
                        : '* * *';
                    return `
                    <div class="result-item">
                        <span class="result-label">Hop ${hop.distance} · ${escapeHtml(addr)}</span>
                        <span class="result-value ${hop.is_alive ? 'success' : ''}">${escapeHtml(rtt)}</span>
                    </div>
                    `;
                }).join('');
                showResult('traceroute-result', rows);
                Toast.show('Traceroute complete!', 'success');
            } else {
                const errorMsg = data.error || 'Trace failed';
                showResult('traceroute-result', `
                    <div class="result-error">
                        <strong>Error:</strong> ${escapeHtml(errorMsg)}
                    </div>
                `);
                Toast.show('Trace failed', 'error');
            }
        } catch (error) {
            showResult('traceroute-result', `
                <div class="result-error">
                    <strong>Request failed:</strong> ${escapeHtml(error.message)}
                </div>
            `);
            Toast.show('Request failed', 'error');
        } finally {
            setButtonLoading(form, false);
        }
    }
};

const WhoisTool = {
    init() {
        const form = document.getElementById('whois-form');
        form?.addEventListener('submit', (e) => this.handleSubmit(e));
    },

    async handleSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const query = form.query.value.trim();

        if (!query) {
            Toast.show('Please enter a domain or IP address', 'warning');
            return;
        }

        setButtonLoading(form, true);
        hideResult('whois-result');

        try {
            const { ok, data } = await API.whois(query);

            if (ok && data.raw) {
                let rows = `
                    <div class="result-item">
                        <span class="result-label">Query</span>
                        <span class="result-value">${escapeHtml(data.query)}</span>
                    </div>
                `;
                if (data.server) {
                    rows += `
                    <div class="result-item">
                        <span class="result-label">WHOIS Server</span>
                        <span class="result-value">${escapeHtml(data.server)}</span>
                    </div>
                    `;
                }
                rows += `<pre class="result-pre">${escapeHtml(data.raw)}</pre>`;
                showResult('whois-result', rows);
                Toast.show('Query successful!', 'success');
            } else {
                const errorMsg = data.error || 'No records found';
                showResult('whois-result', `
                    <div class="result-error">
                        <strong>Error:</strong> ${escapeHtml(errorMsg)}
                    </div>
                `);
                Toast.show('Query failed', 'error');
            }
        } catch (error) {
            showResult('whois-result', `
                <div class="result-error">
                    <strong>Request failed:</strong> ${escapeHtml(error.message)}
                </div>
            `);
            Toast.show('Request failed', 'error');
        } finally {
            setButtonLoading(form, false);
        }
    }
};

const WakeOnLanTool = {
    init() {
        const form = document.getElementById('wol-form');
        form?.addEventListener('submit', (e) => this.handleSubmit(e));
        
        // MAC address formatting
        const macInput = document.getElementById('wol-mac');
        macInput?.addEventListener('input', (e) => this.formatMacAddress(e));
    },

    formatMacAddress(e) {
        let value = e.target.value.toUpperCase().replace(/[^0-9A-F]/g, '');
        
        // Auto-insert colons
        if (value.length > 2) {
            value = value.match(/.{1,2}/g)?.join(':') || value;
        }
        
        // Limit to 17 characters (XX:XX:XX:XX:XX:XX)
        e.target.value = value.substring(0, 17);
    },

    async handleSubmit(e) {
        e.preventDefault();
        const form = e.target;
        let macAddress = form.mac.value.trim();

        // Validate MAC address
        const macPattern = /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/;
        if (!macPattern.test(macAddress)) {
            Toast.show('Please enter a valid MAC address', 'warning');
            return;
        }

        // Normalize MAC address to colon format
        macAddress = macAddress.replace(/-/g, ':').toUpperCase();

        setButtonLoading(form, true);
        hideResult('wol-result');

        try {
            const { ok, data } = await API.wol(macAddress);
            
            if (ok && data.rst === 'success') {
                showResult('wol-result', `
                    <div class="result-item">
                        <span class="result-label">MAC Address</span>
                        <span class="result-value">${escapeHtml(macAddress)}</span>
                    </div>
                    <div class="result-item">
                        <span class="result-label">Status</span>
                        <span class="result-value success">Magic packet sent</span>
                    </div>
                `);
                Toast.show('Magic packet sent!', 'success');
            } else {
                const errorMsg = data.error || 'Send failed';
                showResult('wol-result', `
                    <div class="result-error">
                        <strong>Error:</strong> ${escapeHtml(errorMsg)}
                    </div>
                `);
                Toast.show('Send failed', 'error');
            }
        } catch (error) {
            showResult('wol-result', `
                <div class="result-error">
                    <strong>Request failed:</strong> ${escapeHtml(error.message)}
                </div>
            `);
            Toast.show('Request failed', 'error');
        } finally {
            setButtonLoading(form, false);
        }
    }
};

const PortCheckTool = {
    init() {
        const form = document.getElementById('portcheck-form');
        form?.addEventListener('submit', (e) => this.handleSubmit(e));
    },

    async handleSubmit(e) {
        e.preventDefault();
        const form = e.target;
        const address = form.address.value.trim();
        const port = parseInt(form.port.value) || 80;
        const timeout = parseFloat(form.timeout.value) || 3;

        if (!address) {
            Toast.show('Please enter a target address', 'warning');
            return;
        }

        setButtonLoading(form, true);
        hideResult('portcheck-result');

        try {
            const { ok, status, data } = await API.portCheck(address, port, timeout);

            const statusClass = data.open ? 'success' : 'error';
            const statusText = data.open ? 'Open' : 'Closed';

            let rows = `
                <div class="result-item">
                    <span class="result-label">Target Address</span>
                    <span class="result-value">${escapeHtml(data.address)}</span>
                </div>
                <div class="result-item">
                    <span class="result-label">Port</span>
                    <span class="result-value">${data.port}</span>
                </div>
                <div class="result-item">
                    <span class="result-label">Status</span>
                    <span class="result-value ${statusClass}">${statusText}</span>
                </div>
            `;
            if (data.open && data.latency !== null && data.latency !== undefined) {
                rows += `
                <div class="result-item">
                    <span class="result-label">Latency</span>
                    <span class="result-value success">${formatDelay(data.latency)}</span>
                </div>
                `;
            }
            if (data.error) {
                rows += `
                <div class="result-item">
                    <span class="result-label">Details</span>
                    <span class="result-value">${escapeHtml(data.error)}</span>
                </div>
                `;
            }
            showResult('portcheck-result', rows);
            Toast.show(data.open ? 'Port is open!' : 'Port is closed', data.open ? 'success' : 'warning');
        } catch (error) {
            showResult('portcheck-result', `
                <div class="result-error">
                    <strong>Request failed:</strong> ${escapeHtml(error.message)}
                </div>
            `);
            Toast.show('Request failed', 'error');
        } finally {
            setButtonLoading(form, false);
        }
    }
};

// My IP display
async function loadMyIp() {
    const ipElement = document.getElementById('my-ip');
    if (!ipElement) return;

    try {
        const { ok, data } = await API.getMyIp();
        if (ok && data.ip) {
            ipElement.textContent = data.ip;
        } else {
            ipElement.textContent = 'Failed to load';
        }
    } catch (error) {
        ipElement.textContent = 'Failed to load';
    }
}

// Utility functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize application
document.addEventListener('DOMContentLoaded', () => {
    ThemeManager.init();
    TabManager.init();
    PingTool.init();
    TcpPingTool.init();
    NslookupTool.init();
    DigTool.init();
    ReverseIpTool.init();
    TracerouteTool.init();
    WhoisTool.init();
    WakeOnLanTool.init();
    PortCheckTool.init();
    loadMyIp();
});
