/**
 * Nexus Debug Interface
 * Real-time event monitoring and system debugging for Nexus Framework
 */

class NexusDebug {
    constructor() {
        this.eventSource = null;
        this.isMonitoring = false;
        this.events = [];
        this.eventCount = 0;
        this.eventsPerMinute = 0;
        this.startTime = null;
        this.filterText = '';

        // DOM elements
        this.elements = {};

        // API endpoints
        this.apiBase = '/api/v1';
        this.endpoints = {
            events: `${this.apiBase}/debug/events`,
            plugins: `${this.apiBase}/plugins`,
            system: `${this.apiBase}/system/info`,
            health: `${this.apiBase}/system/health`
        };
    }

    /**
     * Initialize the debug interface
     */
    init() {
        this.bindElements();
        this.setupEventListeners();
        this.loadInitialData();
        this.startStatsUpdater();
    }

    /**
     * Bind DOM elements to properties
     */
    bindElements() {
        this.elements = {
            toggleStream: document.getElementById('toggle-stream'),
            clearEvents: document.getElementById('clear-events'),
            filterInput: document.getElementById('filter-input'),
            eventContainer: document.getElementById('event-container'),
            pluginList: document.getElementById('plugin-list'),
            pluginCount: document.getElementById('plugin-count'),
            eventCount: document.getElementById('event-count'),
            eventsPerMin: document.getElementById('events-per-min'),
            systemStatus: document.getElementById('system-status'),
            appInfo: document.getElementById('app-info'),
            performanceInfo: document.getElementById('performance-info')
        };
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Toggle stream monitoring
        this.elements.toggleStream.addEventListener('click', () => {
            this.toggleEventStream();
        });

        // Clear events
        this.elements.clearEvents.addEventListener('click', () => {
            this.clearEvents();
        });

        // Filter events
        this.elements.filterInput.addEventListener('input', (e) => {
            this.filterText = e.target.value.toLowerCase();
            this.filterEvents();
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 'k':
                        e.preventDefault();
                        this.elements.filterInput.focus();
                        break;
                    case 'e':
                        e.preventDefault();
                        this.toggleEventStream();
                        break;
                    case 'l':
                        e.preventDefault();
                        this.clearEvents();
                        break;
                }
            }
        });
    }

    /**
     * Load initial data
     */
    async loadInitialData() {
        await Promise.all([
            this.loadPlugins(),
            this.loadSystemInfo(),
            this.loadSystemHealth()
        ]);
    }

    /**
     * Toggle event stream monitoring
     */
    toggleEventStream() {
        if (this.isMonitoring) {
            this.stopEventStream();
        } else {
            this.startEventStream();
        }
    }

    /**
     * Start event stream monitoring
     */
    startEventStream() {
        if (this.isMonitoring) return;

        try {
            this.eventSource = new EventSource(`${this.endpoints.events}/stream`);

            this.eventSource.onopen = () => {
                this.isMonitoring = true;
                this.startTime = new Date();
                this.updateStreamButton();
                this.showNotification('Event monitoring started', 'success');
            };

            this.eventSource.onmessage = (event) => {
                try {
                    const eventData = JSON.parse(event.data);
                    this.addEvent(eventData);
                } catch (error) {
                    console.error('Error parsing event data:', error);
                }
            };

            this.eventSource.onerror = (error) => {
                console.error('EventSource error:', error);
                this.stopEventStream();
                this.showNotification('Event stream error', 'error');
            };

        } catch (error) {
            console.error('Failed to start event stream:', error);
            this.showNotification('Failed to start monitoring', 'error');
        }
    }

    /**
     * Stop event stream monitoring
     */
    stopEventStream() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }

        this.isMonitoring = false;
        this.updateStreamButton();
        this.showNotification('Event monitoring stopped', 'info');
    }

    /**
     * Update stream button state
     */
    updateStreamButton() {
        const button = this.elements.toggleStream;
        if (this.isMonitoring) {
            button.textContent = '⏸️ Stop Monitor';
            button.className = 'btn btn-secondary';
        } else {
            button.textContent = '▶️ Start Monitor';
            button.className = 'btn btn-primary';
        }
    }

    /**
     * Add event to the display
     */
    addEvent(eventData) {
        this.events.unshift({
            ...eventData,
            timestamp: new Date()
        });

        // Limit events to prevent memory issues
        if (this.events.length > 1000) {
            this.events = this.events.slice(0, 1000);
        }

        this.eventCount++;
        this.updateEventCount();
        this.renderEvents();
    }

    /**
     * Clear all events
     */
    clearEvents() {
        this.events = [];
        this.eventCount = 0;
        this.updateEventCount();
        this.renderEvents();
        this.showNotification('Events cleared', 'info');
    }

    /**
     * Filter events based on search text
     */
    filterEvents() {
        this.renderEvents();
    }

    /**
     * Render events in the container
     */
    renderEvents() {
        const container = this.elements.eventContainer;

        if (this.events.length === 0) {
            container.innerHTML = '<div class="no-events">No events captured yet. Click "Start Monitor" to begin.</div>';
            return;
        }

        const filteredEvents = this.events.filter(event => {
            if (!this.filterText) return true;

            const searchableText = [
                event.type || '',
                event.plugin || '',
                JSON.stringify(event.data || {})
            ].join(' ').toLowerCase();

            return searchableText.includes(this.filterText);
        });

        if (filteredEvents.length === 0) {
            container.innerHTML = '<div class="no-events">No events match your filter.</div>';
            return;
        }

        const eventsHtml = filteredEvents.slice(0, 100).map(event => {
            const timestamp = event.timestamp.toLocaleTimeString();
            const type = event.type || 'unknown';
            const plugin = event.plugin ? `[${event.plugin}]` : '';
            const data = JSON.stringify(event.data || {}, null, 2);

            return `
                <div class="event-item fade-in">
                    <span class="event-timestamp">${timestamp}</span>
                    <span class="event-type">${type}</span>
                    <span class="event-plugin">${plugin}</span>
                    <div class="event-data">${data}</div>
                </div>
            `;
        }).join('');

        container.innerHTML = eventsHtml;

        // Auto-scroll to top for new events
        container.scrollTop = 0;
    }

    /**
     * Update event count display
     */
    updateEventCount() {
        this.elements.eventCount.textContent = this.eventCount;
    }

    /**
     * Start stats updater
     */
    startStatsUpdater() {
        setInterval(() => {
            this.updateEventsPerMinute();
        }, 10000); // Update every 10 seconds
    }

    /**
     * Update events per minute calculation
     */
    updateEventsPerMinute() {
        if (!this.startTime || !this.isMonitoring) {
            this.eventsPerMinute = 0;
        } else {
            const minutesElapsed = (new Date() - this.startTime) / (1000 * 60);
            this.eventsPerMinute = minutesElapsed > 0 ? Math.round(this.eventCount / minutesElapsed) : 0;
        }

        this.elements.eventsPerMin.textContent = this.eventsPerMinute;
    }

    /**
     * Load plugins data
     */
    async loadPlugins() {
        try {
            const response = await fetch(this.endpoints.plugins);
            if (!response.ok) throw new Error('Failed to fetch plugins');

            const plugins = await response.json();
            this.renderPlugins(plugins);
            this.elements.pluginCount.textContent = plugins.length;

        } catch (error) {
            console.error('Error loading plugins:', error);
            this.elements.pluginList.innerHTML = '<div class="error">Failed to load plugins</div>';
        }
    }

    /**
     * Render plugins grid
     */
    renderPlugins(plugins) {
        if (!plugins || plugins.length === 0) {
            this.elements.pluginList.innerHTML = '<div class="no-plugins">No plugins loaded</div>';
            return;
        }

        const pluginsHtml = plugins.map(plugin => {
            const statusClass = plugin.enabled ? 'active' : 'inactive';
            const statusIcon = plugin.enabled ? '🟢' : '⭕';

            return `
                <div class="plugin-card">
                    <h4>
                        ${statusIcon} ${plugin.name}
                        <span class="plugin-status ${statusClass}"></span>
                    </h4>
                    <p class="text-sm text-secondary">${plugin.description || 'No description'}</p>
                    <div class="plugin-meta">
                        <span class="text-xs">v${plugin.version}</span>
                        <span class="text-xs">${plugin.category || 'general'}</span>
                    </div>
                </div>
            `;
        }).join('');

        this.elements.pluginList.innerHTML = pluginsHtml;
    }

    /**
     * Load system information
     */
    async loadSystemInfo() {
        try {
            const response = await fetch(this.endpoints.system);
            if (!response.ok) throw new Error('Failed to fetch system info');

            const info = await response.json();
            this.renderSystemInfo(info);

        } catch (error) {
            console.error('Error loading system info:', error);
            this.elements.appInfo.textContent = 'Failed to load system info';
        }
    }

    /**
     * Render system information
     */
    renderSystemInfo(info) {
        const appInfo = `
            Application: ${info.app?.name || 'Unknown'}<br>
            Version: ${info.app?.version || 'Unknown'}<br>
            Environment: ${info.environment || 'Unknown'}<br>
            Uptime: ${this.formatUptime(info.uptime)}
        `;

        const perfInfo = `
            Memory: ${this.formatBytes(info.memory?.used || 0)} / ${this.formatBytes(info.memory?.total || 0)}<br>
            CPU: ${info.cpu?.usage || 0}%<br>
            Load: ${info.load?.average || 'N/A'}<br>
            Requests: ${info.requests?.total || 0}
        `;

        this.elements.appInfo.innerHTML = appInfo;
        this.elements.performanceInfo.innerHTML = perfInfo;
    }

    /**
     * Load system health
     */
    async loadSystemHealth() {
        try {
            const response = await fetch(this.endpoints.health);
            if (!response.ok) throw new Error('Failed to fetch health status');

            const health = await response.json();
            this.updateSystemStatus(health.status);

        } catch (error) {
            console.error('Error loading system health:', error);
            this.updateSystemStatus('error');
        }
    }

    /**
     * Update system status display
     */
    updateSystemStatus(status) {
        const statusMap = {
            'healthy': '🟢 Online',
            'degraded': '🟡 Degraded',
            'unhealthy': '🔴 Issues',
            'error': '❌ Error'
        };

        this.elements.systemStatus.textContent = statusMap[status] || '❓ Unknown';
    }

    /**
     * Format bytes to human readable
     */
    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    /**
     * Format uptime to human readable
     */
    formatUptime(seconds) {
        if (!seconds) return 'Unknown';

        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);

        if (days > 0) return `${days}d ${hours}h ${minutes}m`;
        if (hours > 0) return `${hours}h ${minutes}m`;
        return `${minutes}m`;
    }

    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        // Simple console notification for now
        // In a full implementation, this would show a toast notification
        const styles = {
            success: 'color: green',
            error: 'color: red',
            warning: 'color: orange',
            info: 'color: blue'
        };

        console.log(`%c${message}`, styles[type] || styles.info);
    }

    /**
     * Refresh plugins data
     */
    async refreshPlugins() {
        await this.loadPlugins();
        this.showNotification('Plugins refreshed', 'success');
    }
}

// Global functions for quick actions
window.sendTestEvent = async function() {
    try {
        const response = await fetch('/api/v1/debug/test-event', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: 'test',
                data: { message: 'Test event from debug interface', timestamp: new Date().toISOString() }
            })
        });

        if (response.ok) {
            console.log('%cTest event sent successfully', 'color: green');
        } else {
            throw new Error('Failed to send test event');
        }
    } catch (error) {
        console.error('Error sending test event:', error);
    }
};

window.refreshPlugins = function() {
    if (window.nexusDebug) {
        window.nexusDebug.refreshPlugins();
    }
};

window.exportEvents = function() {
    if (window.nexusDebug && window.nexusDebug.events.length > 0) {
        const data = JSON.stringify(window.nexusDebug.events, null, 2);
        const blob = new Blob([data], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `nexus-events-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
        console.log('%cEvents exported successfully', 'color: green');
    } else {
        console.log('%cNo events to export', 'color: orange');
    }
};

window.showSystemHealth = async function() {
    try {
        const response = await fetch('/api/v1/system/health');
        if (!response.ok) throw new Error('Failed to fetch health status');

        const health = await response.json();
        console.group('System Health Status');
        console.log('Overall Status:', health.status);
        console.log('Components:', health.components);
        console.log('Checks:', health.checks);
        console.groupEnd();
    } catch (error) {
        console.error('Error fetching system health:', error);
    }
};

// Export the class and create global instance
window.NexusDebug = NexusDebug;
window.nexusDebug = null;

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.nexusDebug = new NexusDebug();
});
